# Life Insurance Platform — Onboarding & RBAC Remediation Guide

**Project:** Zanzibar Insurance Commission - Life Insurance Platform  
**Created:** 2026-06-26  
**Purpose:** Systematic remediation of architectural flaws, hardcoded parameters, and RBAC gaps  
**Status Tracking:** Mark checkboxes as items are completed

---

## Table of Contents

1. [Critical Blockers](#1-critical-blockers)
2. [Hardcoded Parameters Remediation](#2-hardcoded-parameters-remediation)
3. [Onboarding Pipeline Fixes](#3-onboarding-pipeline-fixes)
4. [RBAC Implementation](#4-rbac-implementation)
5. [Database Seeding Requirements](#5-database-seeding-requirements)
6. [Frontend Integration](#6-frontend-integration)
7. [Testing & Validation](#7-testing--validation)

---

## 1. Critical Blockers

### Blocker 1.1: Remove Database Constraint on Partner Type

**File:** `backend/apps/partner_onboarding/models.py:158-161`  
**Impact:** Physically prevents new partner types from being saved  
**Priority:** BLOCKER  

- [ ] **Create migration to remove constraint**
  ```python
  # migrations/0003_remove_partner_type_constraint.py
  operations = [
      migrations.RemoveConstraint(
          model_name='partnerapplication',
          name='valid_partner_type',
      ),
      migrations.AlterField(
          model_name='partnerapplication',
          name='partner_type',
          field=models.CharField(max_length=50),  # Remove choices=
      ),
  ]
  ```

- [ ] **Run migration**
  ```bash
  cd backend
  python manage.py makemigrations partner_onboarding
  python manage.py migrate
  ```

- [ ] **Verify constraint removed from database**
  ```sql
  SELECT * FROM sqlite_master WHERE type='table' AND name='partner_onboarding_partnerapplication';
  ```

**Completed:** _____

---

### Blocker 1.2: Route Approvals Through Governance Module

**Files:**  
- `backend/apps/partner_onboarding/services/application_service.py:150-167`
- `backend/apps/governance/services/approval_service.py`

**Impact:** No maker/checker separation, no audit trail  
**Priority:** BLOCKER  

- [ ] **Refactor ApplicationService to use ApprovalService**
  ```python
  # backend/apps/partner_onboarding/services/application_service.py
  
  from apps.governance.services.approval_service import ApprovalService
  
  class ApplicationService:
      def submit_for_approval(self, application, submitted_by):
          # Validate state transition
          self.workflow_engine.validate_transition(application.status, 'PENDING_APPROVAL')
          
          # Create approval request in governance module
          approval = ApprovalService.submit(
              entity_type='partner_application',
              entity_id=application.id,
              submitted_by=submitted_by,
              approval_type='PARTNER_ONBOARDING',
              metadata={
                  'partner_name': application.full_name,
                  'partner_types': list(application.partner_types.values_list('code', flat=True)),
                  'risk_score': application.risk_score,
                  'compliance_status': application.compliance_status,
              }
          )
          
          application.status = 'PENDING_APPROVAL'
          application.save()
          
          return approval
      
      def approve(self, application, approved_by):
          # Only called by governance signal handler
          self.workflow_engine.validate_transition(application.status, 'APPROVED')
          application.status = 'APPROVED'
          application.approved_by = approved_by
          application.approved_at = timezone.now()
          application.save()
  ```

- [ ] **Create signal handler for approval completion**
  ```python
  # backend/apps/governance/signals.py (new file)
  from django.dispatch import Signal, receiver
  
  approval_status_changed = Signal()
  
  @receiver(approval_status_changed)
  def handle_partner_approval(sender, approval_request, **kwargs):
      if approval_request.entity_type != 'partner_application':
          return
          
      from apps.partner_onboarding.services.application_service import ApplicationService
      from apps.partner_onboarding.models import PartnerApplication
      
      application = PartnerApplication.objects.get(id=approval_request.entity_id)
      service = ApplicationService()
      
      if approval_request.status == 'APPROVED':
          service.approve(application, approved_by=approval_request.approved_by)
      elif approval_request.status == 'REJECTED':
          service.reject(application, reason=approval_request.comments, rejected_by=approval_request.approved_by)
  ```

- [ ] **Update ApprovalService to emit signal**
  ```python
  # backend/apps/governance/services/approval_service.py
  from apps.governance.signals import approval_status_changed
  
  class ApprovalService:
      @staticmethod
      def approve(approval_id, approved_by, comments=''):
          approval = ApprovalRequest.objects.get(id=approval_id)
          approval.status = 'APPROVED'
          approval.approved_by = approved_by
          approval.comments = comments
          approval.approved_at = timezone.now()
          approval.save()
          
          # Emit signal
          approval_status_changed.send(
              sender=ApprovalService,
              approval_request=approval
          )
          
          return approval
  ```

- [ ] **Test approval flow end-to-end**
  - Submit application for approval
  - Verify ApprovalRequest created in governance module
  - Approve via governance endpoint
  - Verify application status updated to APPROVED

**Completed:** _____

---

### Blocker 1.3: Implement Role-Conditional Document Upload

**Files:**  
- `insurance-dashboard-ui/src/pages/onboarding/ApplicationForm.tsx:328-377`
- `backend/apps/partner_onboarding/views.py`

**Impact:** Documents not filtered by partner roles  
**Priority:** BLOCKER  

- [ ] **Create backend API endpoint for required documents**
  ```python
  # backend/apps/partner_onboarding/views.py
  
  from apps.partners.models import PartnerTypeDocumentRequirement
  from rest_framework.decorators import api_view
  
  @api_view(['GET'])
  def get_required_documents(request, application_id):
      """Fetch required documents based on assigned partner types"""
      try:
          application = PartnerApplication.objects.get(id=application_id)
          partner_types = application.partner_types.values_list('partner_type__code', flat=True)
          
          requirements = PartnerTypeDocumentRequirement.objects.filter(
              partner_type__code__in=partner_types,
              is_active=True
          ).values(
              'document_type',
              'is_mandatory',
              'description',
              'max_file_size_mb',
              'accepted_formats'
          )
          
          # Merge requirements for multiple partner types
          merged_docs = {}
          for req in requirements:
              doc_type = req['document_type']
              if doc_type not in merged_docs:
                  merged_docs[doc_type] = req
              else:
                  # If any role requires it, mark as mandatory
                  merged_docs[doc_type]['is_mandatory'] = (
                      merged_docs[doc_type]['is_mandatory'] or req['is_mandatory']
                  )
          
          return Response({
              'documents': list(merged_docs.values()),
              'partner_types': list(partner_types)
          })
          
      except PartnerApplication.DoesNotExist:
          return Response({'error': 'Application not found'}, status=404)
  ```

- [ ] **Add URL route**
  ```python
  # backend/apps/partner_onboarding/urls.py
  urlpatterns = [
      # ... existing routes
      path(
          'applications/<int:application_id>/required-documents/',
          views.get_required_documents,
          name='application-required-documents'
      ),
  ]
  ```

- [ ] **Update frontend to fetch required documents**
  ```typescript
  // insurance-dashboard-ui/src/hooks/useRequiredDocuments.ts
  
  import { useQuery } from '@tanstack/react-query'
  import { api } from '@/lib/api'
  
  export interface DocumentRequirement {
    document_type: string
    is_mandatory: boolean
    description: string
    max_file_size_mb: number
    accepted_formats: string[]
  }
  
  export function useRequiredDocuments(applicationId: number | null) {
    return useQuery({
      queryKey: ['required-documents', applicationId],
      queryFn: async () => {
        const response = await api.get(
          `/api/v1/onboarding/applications/${applicationId}/required-documents/`
        )
        return response.data.documents as DocumentRequirement[]
      },
      enabled: !!applicationId,
    })
  }
  ```

- [ ] **Update ApplicationForm component**
  ```typescript
  // insurance-dashboard-ui/src/pages/onboarding/ApplicationForm.tsx
  
  import { useRequiredDocuments } from '@/hooks/useRequiredDocuments'
  
  export function ApplicationForm({ applicationId }: { applicationId: number }) {
    const { data: requiredDocs, isLoading } = useRequiredDocuments(applicationId)
    
    if (isLoading) return <div>Loading document requirements...</div>
    
    return (
      <div>
        <h3>Required Documents</h3>
        {requiredDocs?.map(doc => (
          <div key={doc.document_type}>
            <label>
              {doc.description}
              {doc.is_mandatory && <span className="text-red-500"> *</span>}
            </label>
            <input 
              type="file" 
              accept={doc.accepted_formats.join(',')}
              required={doc.is_mandatory}
            />
            <small>Max size: {doc.max_file_size_mb}MB</small>
          </div>
        ))}
      </div>
    )
  }
  ```

- [ ] **Test with multiple partner types**
  - Create application with INDIVIDUAL role
  - Verify only INDIVIDUAL documents shown
  - Add AGENT role
  - Verify AGENT documents added to list
  - Verify mandatory flags correct

**Completed:** _____

---

### Blocker 1.4: Protect System Parameters Endpoints

**File:** `backend/apps/system_parameters/views.py:15-53`  
**Impact:** Any authenticated user can modify system configuration  
**Priority:** BLOCKER  

- [ ] **Create HasModulePermission class (if not exists)**
  ```python
  # backend/apps/core/permissions.py
  
  from rest_framework.permissions import BasePermission
  
  class HasModulePermission(BasePermission):
      """
      Permission class that checks if user has specific module permission
      Usage: permission_classes = [HasModulePermission]
             module_code = 'system_parameters'
             required_action = 'MANAGE'
      """
      module_code = None
      required_action = None
      
      def has_permission(self, request, view):
          if not request.user or not request.user.is_authenticated:
              return False
          
          # Get module and action from view or class
          module = getattr(view, 'module_code', self.module_code)
          action = getattr(view, 'required_action', self.required_action)
          
          if not module:
              return False
          
          # Default action based on HTTP method
          if not action:
              method_actions = {
                  'GET': 'READ',
                  'POST': 'CREATE',
                  'PUT': 'UPDATE',
                  'PATCH': 'UPDATE',
                  'DELETE': 'DELETE',
              }
              action = method_actions.get(request.method, 'READ')
          
          return request.user.has_module_permission(module, action)
  ```

- [ ] **Add user.has_module_permission method**
  ```python
  # backend/apps/users/models.py
  
  class User(AbstractUser):
      # ... existing fields ...
      
      def has_module_permission(self, module_code, action='READ'):
          """Check if user has permission for specific module and action"""
          if self.is_superuser:
              return True
          
          return self.groups.filter(
              permissions__module=module_code,
              permissions__action=action,
              permissions__is_active=True
          ).exists()
      
      def get_all_permissions(self):
          """Get all permissions for user"""
          if self.is_superuser:
              return list(UserPermission.objects.values_list('module', 'action'))
          
          return list(
              self.groups.filter(
                  permissions__is_active=True
              ).values_list('permissions__module', 'permissions__action')
          )
  ```

- [ ] **Protect SystemParameterViewSet**
  ```python
  # backend/apps/system_parameters/views.py
  
  from apps.core.permissions import HasModulePermission
  
  class SystemParameterViewSet(viewsets.ModelViewSet):
      queryset = SystemParameter.objects.all()
      serializer_class = SystemParameterSerializer
      module_code = 'system_parameters'
      
      def get_permissions(self):
          if self.action in ['list', 'retrieve']:
              return [permissions.IsAuthenticated()]
          return [permissions.IsAuthenticated(), HasModulePermission()]
  
  class ChoiceListViewSet(viewsets.ModelViewSet):
      queryset = ChoiceList.objects.all()
      serializer_class = ChoiceListSerializer
      module_code = 'system_parameters'
      
      def get_permissions(self):
          if self.action in ['list', 'retrieve']:
              return [permissions.IsAuthenticated()]
          return [permissions.IsAuthenticated(), HasModulePermission()]
  ```

- [ ] **Test protection**
  - Login as regular user (PORTAL_USER)
  - Attempt to create/update system parameter
  - Verify 403 Forbidden response
  - Login as admin with system_parameters:MANAGE permission
  - Verify can create/update parameters

**Completed:** _____

---

### Blocker 1.5: Fix KYC Status Mismatch

**Files:**  
- `insurance-dashboard-ui/src/lib/types.ts:727`
- `backend/apps/partners/models.py:321-327`

**Impact:** Frontend and backend use different KYC status values  
**Priority:** CRITICAL  

- [ ] **Align frontend types with backend**
  ```typescript
  // insurance-dashboard-ui/src/lib/types.ts
  
  export type KYCStatus = 
    | "NOT_SET"
    | "PENDING_REVIEW"
    | "VERIFIED"
    | "REJECTED"
    | "EXPIRED"
  ```

- [ ] **Update all frontend components using KYC status**
  ```typescript
  // Search for and update all references to old status values
  // PENDING -> PENDING_REVIEW
  // CLEARED -> VERIFIED
  // ESCALATED -> REJECTED (or appropriate mapping)
  ```

- [ ] **Create status label mapping**
  ```typescript
  // insurance-dashboard-ui/src/constants/kyc.ts
  
  export const KYC_STATUS_LABELS: Record<KYCStatus, string> = {
    NOT_SET: "Not Set",
    PENDING_REVIEW: "Pending Review",
    VERIFIED: "Verified",
    REJECTED: "Rejected",
    EXPIRED: "Expired",
  }
  
  export const KYC_STATUS_COLORS: Record<KYCStatus, string> = {
    NOT_SET: "gray",
    PENDING_REVIEW: "yellow",
    VERIFIED: "green",
    REJECTED: "red",
    EXPIRED: "orange",
  }
  ```

- [ ] **Test KYC workflow**
  - Submit application with KYC documents
  - Verify status shows PENDING_REVIEW
  - Verify officer can mark as VERIFIED
  - Verify frontend displays correct status

**Completed:** _____

---

### Blocker 1.6: Implement Permission-Based Route Guards

**File:** `insurance-dashboard-ui/src/App.tsx:37-40`  
**Impact:** All authenticated users can access all routes  
**Priority:** BLOCKER  

- [ ] **Create RequirePermission component**
  ```typescript
  // insurance-dashboard-ui/src/components/RequirePermission.tsx
  
  import { Navigate } from 'react-router-dom'
  import { useAuth } from '@/hooks/useAuth'
  
  interface RequirePermissionProps {
    permission: string
    children: React.ReactNode
  }
  
  export function RequirePermission({ permission, children }: RequirePermissionProps) {
    const { user, isLoading } = useAuth()
    
    if (isLoading) {
      return <div>Loading...</div>
    }
    
    if (!user) {
      return <Navigate to="/login" replace />
    }
    
    // Check if user has permission
    const hasPermission = user.permissions?.some(p => 
      `${p.module}:${p.action}` === permission
    )
    
    if (!hasPermission) {
      return <Navigate to="/unauthorized" replace />
    }
    
    return <>{children}</>
  }
  ```

- [ ] **Update useAuth hook to include permissions**
  ```typescript
  // insurance-dashboard-ui/src/hooks/useAuth.ts
  
  interface AuthUser {
    id: number
    username: string
    email: string
    userType: string
    permissions: Array<{ module: string; action: string }>
    groups: string[]
  }
  
  export function useAuth() {
    const [user, setUser] = useState<AuthUser | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    
    useEffect(() => {
      const token = localStorage.getItem('accessToken')
      if (token) {
        api.get('/api/v1/auth/me/')
          .then(response => {
            setUser({
              ...response.data.user,
              permissions: response.data.user.permissions || [],
              groups: response.data.user.groups || [],
            })
          })
          .catch(() => {
            localStorage.removeItem('accessToken')
          })
          .finally(() => setIsLoading(false))
      } else {
        setIsLoading(false)
      }
    }, [])
    
    return { user, isLoading, accessToken: localStorage.getItem('accessToken') }
  }
  ```

- [ ] **Protect routes in App.tsx**
  ```typescript
  // insurance-dashboard-ui/src/App.tsx
  
  import { RequirePermission } from '@/components/RequirePermission'
  
  function App() {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        
        <Route element={<RequireAuth><Layout /></RequireAuth>}>
          <Route path="/" element={<Dashboard />} />
          
          <Route path="/system-parameters" element={
            <RequirePermission permission="system_parameters:MANAGE">
              <SystemParameters />
            </RequirePermission>
          } />
          
          <Route path="/users" element={
            <RequirePermission permission="users:MANAGE">
              <UserManagement />
            </RequirePermission>
          } />
          
          <Route path="/approvals" element={
            <RequirePermission permission="governance:APPROVE">
              <Approvals />
            </RequirePermission>
          } />
          
          <Route path="/onboarding" element={
            <RequirePermission permission="partner_onboarding:CREATE">
              <OnboardingList />
            </RequirePermission>
          } />
          
          <Route path="/unauthorized" element={<Unauthorized />} />
        </Route>
      </Routes>
    )
  }
  ```

- [ ] **Create Unauthorized page**
  ```typescript
  // insurance-dashboard-ui/src/pages/Unauthorized.tsx
  
  export function Unauthorized() {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <h1 className="text-2xl font-bold text-red-600">Access Denied</h1>
        <p className="mt-4">You do not have permission to view this page.</p>
        <Link to="/" className="mt-6 text-blue-600 hover:underline">
          Return to Dashboard
        </Link>
      </div>
    )
  }
  ```

- [ ] **Test route protection**
  - Login as user without system_parameters permission
  - Navigate to /system-parameters
  - Verify redirected to /unauthorized
  - Login as admin with permission
  - Verify can access page

**Completed:** _____

---

### Blocker 1.7: Protect Partner Configuration Endpoints

**File:** `backend/apps/partners/views.py:329-563`  
**Impact:** Any authenticated user can modify document/field requirements  
**Priority:** BLOCKER  

- [ ] **Add permission checks to all configuration ViewSets**
  ```python
  # backend/apps/partners/views.py
  
  from apps.core.permissions import HasModulePermission
  
  class PartnerTypeDocumentRequirementViewSet(viewsets.ModelViewSet):
      queryset = PartnerTypeDocumentRequirement.objects.all()
      serializer_class = PartnerTypeDocumentRequirementSerializer
      module_code = 'partner_config'
      
      def get_permissions(self):
          if self.action in ['list', 'retrieve']:
              return [permissions.IsAuthenticated()]
          return [permissions.IsAuthenticated(), HasModulePermission()]
  
  class PartnerTypeFieldConfigurationViewSet(viewsets.ModelViewSet):
      queryset = PartnerTypeFieldConfiguration.objects.all()
      serializer_class = PartnerTypeFieldConfigurationSerializer
      module_code = 'partner_config'
      
      def get_permissions(self):
          if self.action in ['list', 'retrieve']:
              return [permissions.IsAuthenticated()]
          return [permissions.IsAuthenticated(), HasModulePermission()]
  
  class PartnerTypeContactRequirementViewSet(viewsets.ModelViewSet):
      queryset = PartnerTypeContactRequirement.objects.all()
      serializer_class = PartnerTypeContactRequirementSerializer
      module_code = 'partner_config'
      
      def get_permissions(self):
          if self.action in ['list', 'retrieve']:
              return [permissions.IsAuthenticated()]
          return [permissions.IsAuthenticated(), HasModulePermission()]
  
  class PartnerTypeBankRequirementViewSet(viewsets.ModelViewSet):
      queryset = PartnerTypeBankRequirement.objects.all()
      serializer_class = PartnerTypeBankRequirementSerializer
      module_code = 'partner_config'
      
      def get_permissions(self):
          if self.action in ['list', 'retrieve']:
              return [permissions.IsAuthenticated()]
          return [permissions.IsAuthenticated(), HasModulePermission()]
  ```

- [ ] **Test all configuration endpoints**
  - Verify read access for authenticated users
  - Verify write access requires partner_config:CREATE/UPDATE/DELETE

**Completed:** _____

---

## 2. Hardcoded Parameters Remediation

### 2.1 Partner Types & Categories

- [ ] **Remove hardcoded choices from partner_onboarding/models.py:36-39**
  ```python
  # BEFORE (line 36-39)
  PARTNER_TYPE_CHOICES = [
      ("INDIVIDUAL", "Individual"),
      ("CORPORATE", "Corporate"),
  ]
  
  # AFTER - Remove this constant entirely
  # Validation will happen in serializer using ConfigurationService
  ```

- [ ] **Remove hardcoded choices from partners/models.py:11-22**
  ```python
  # BEFORE (lines 11-22)
  PARTNER_CATEGORY_CHOICES = [...]
  PARTNER_TYPE_CHOICES = [...]
  
  # AFTER - Remove these constants
  # Use ConfigurationService.get_choice_list() instead
  ```

- [ ] **Update model fields to remove choices parameter**
  ```python
  # backend/apps/partner_onboarding/models.py
  
  class PartnerApplication(models.Model):
      partner_type = models.CharField(max_length=50)  # Remove choices=PARTNER_TYPE_CHOICES
  ```

- [ ] **Update filters to use dynamic choices**
  ```python
  # backend/apps/partner_onboarding/filters.py
  
  from apps.system_parameters.services.config_service import ConfigurationService
  
  def get_partner_type_choices():
      choices = ConfigurationService.get_choice_list('PARTNER_TYPE_CHOICES')
      return [(c['value'], c['label']) for c in choices]
  
  class PartnerApplicationFilter(django_filters.FilterSet):
      partner_type = django_filters.ChoiceFilter(choices=get_partner_type_choices)
  ```

- [ ] **Update serializers to validate dynamically**
  ```python
  # backend/apps/partner_onboarding/serializers.py
  
  from apps.system_parameters.services.config_service import ConfigurationService
  
  class PartnerApplicationSerializer(serializers.ModelSerializer):
      def validate_partner_type(self, value):
          valid_types = ConfigurationService.get_choice_list('PARTNER_TYPE_CHOICES')
          valid_values = [choice['value'] for choice in valid_types]
          
          if value not in valid_values:
              raise ValidationError(f"Invalid partner type. Valid types: {valid_values}")
          
          return value
  ```

- [ ] **Update frontend types**
  ```typescript
  // insurance-dashboard-ui/src/lib/types.ts
  
  // BEFORE
  export type PartnerType = "INDIVIDUAL" | "CORPORATE"
  
  // AFTER
  export type PartnerType = string  // Dynamically fetched from API
  ```

- [ ] **Update frontend to fetch partner types dynamically**
  ```typescript
  // insurance-dashboard-ui/src/hooks/useChoices.ts
  
  import { useQuery } from '@tanstack/react-query'
  import { api } from '@/lib/api'
  
  export interface ChoiceOption {
    value: string
    label: string
    description?: string
  }
  
  export function useChoices(listCode: string) {
    return useQuery({
      queryKey: ['choices', listCode],
      queryFn: async () => {
        const response = await api.get(`/api/v1/system/choices/${listCode}/options/`)
        return response.data.options as ChoiceOption[]
      },
      staleTime: 5 * 60 * 1000, // 5 minutes
    })
  }
  
  // Usage in components
  const { data: partnerTypes } = useChoices('PARTNER_TYPE_CHOICES')
  ```

- [ ] **Update OnboardingList.tsx to use dynamic choices**
  ```typescript
  // insurance-dashboard-ui/src/pages/onboarding/OnboardingList.tsx
  
  import { useChoices } from '@/hooks/useChoices'
  
  export function OnboardingList() {
    const { data: partnerTypes } = useChoices('PARTNER_TYPE_CHOICES')
    const { data: statuses } = useChoices('APPLICATION_STATUS_CHOICES')
    
    const typeOptions = [
      { value: "", label: "All Types" },
      ...(partnerTypes?.map(t => ({ value: t.value, label: t.label })) || [])
    ]
    
    const statusOptions = [
      { value: "", label: "All Statuses" },
      ...(statuses?.map(s => ({ value: s.value, label: s.label })) || [])
    ]
    
    // Use typeOptions and statusOptions in filters
  }
  ```

**Completed:** _____

---

### 2.2 Application Statuses

- [ ] **Remove hardcoded status choices from partner_onboarding/models.py:23-34**
  ```python
  # BEFORE
  APPLICATION_STATUS_CHOICES = [
      ("ACTIVE", "Active"),
      ("DRAFT", "Draft"),
      # ... 10 more
  ]
  
  # AFTER - Remove constant, use dynamic validation
  ```

- [ ] **Update model field**
  ```python
  class PartnerApplication(models.Model):
      status = models.CharField(max_length=50, default='DRAFT')  # Remove choices=
  ```

- [ ] **Update filters**
  ```python
  # backend/apps/partner_onboarding/filters.py
  
  def get_status_choices():
      choices = ConfigurationService.get_choice_list('APPLICATION_STATUS_CHOICES')
      return [(c['value'], c['label']) for c in choices]
  
  class PartnerApplicationFilter(django_filters.FilterSet):
      status = django_filters.ChoiceFilter(choices=get_status_choices)
  ```

- [ ] **Update frontend types**
  ```typescript
  // insurance-dashboard-ui/src/lib/types.ts
  
  // BEFORE
  export type ApplicationStatus = "ACTIVE" | "DRAFT" | "SUBMITTED" | ...
  
  // AFTER
  export type ApplicationStatus = string
  ```

- [ ] **Update frontend components to fetch statuses**
  ```typescript
  // Use useChoices('APPLICATION_STATUS_CHOICES') in all components
  ```

**Completed:** _____

---

### 2.3 Document Types

- [ ] **Remove hardcoded document types from partner_onboarding/models.py:41-54**
  ```python
  # BEFORE
  DOCUMENT_TYPE_CHOICES = [
      ("NATIONAL_ID", "National ID"),
      ("PASSPORT", "Passport"),
      # ... 10 more
  ]
  
  # AFTER - Remove constant
  ```

- [ ] **Update model field**
  ```python
  class ApplicationDocument(models.Model):
      document_type = models.CharField(max_length=100)  # Remove choices=
  ```

- [ ] **Update frontend to fetch document types**
  ```typescript
  const { data: documentTypes } = useChoices('DOCUMENT_TYPE_CHOICES')
  ```

**Completed:** _____

---

### 2.4 Demographic Choices (Gender, Nationality, Industry, etc.)

- [ ] **Remove all hardcoded demographic choices from partners/models.py**
  ```python
  # Remove these constants:
  # TITLE_CHOICES (lines 41-51)
  # GENDER_CHOICES (lines 53-56)
  # MARITAL_STATUS_CHOICES (lines 58-64)
  # POLITICAL_RISK_CHOICES (lines 66-71)
  # AML_RISK_CHOICES (lines 73-77)
  # INDUSTRY_CHOICES (lines 79-110)
  # NATIONALITY_CHOICES (lines 112-133)
  ```

- [ ] **Update model fields**
  ```python
  class IndividualProfile(models.Model):
      title = models.CharField(max_length=50, blank=True)
      gender = models.CharField(max_length=50, blank=True)
      nationality = models.CharField(max_length=100, blank=True)
      industry = models.CharField(max_length=100, blank=True)
      # All without choices= parameter
  ```

- [ ] **Update filters to use dynamic choices**
  ```python
  # backend/apps/partners/filters.py
  
  def get_gender_choices():
      choices = ConfigurationService.get_choice_list('GENDER_CHOICES')
      return [(c['value'], c['label']) for c in choices]
  
  class IndividualProfileFilter(django_filters.FilterSet):
      gender = django_filters.ChoiceFilter(choices=get_gender_choices)
      nationality = django_filters.ChoiceFilter(choices=get_nationality_choices)
      industry = django_filters.ChoiceFilter(choices=get_industry_choices)
  ```

- [ ] **Update frontend to fetch all demographic choices**
  ```typescript
  const { data: genders } = useChoices('GENDER_CHOICES')
  const { data: nationalities } = useChoices('NATIONALITY_CHOICES')
  const { data: industries } = useChoices('INDUSTRY_CHOICES')
  const { data: titles } = useChoices('TITLE_CHOICES')
  const { data: maritalStatuses } = useChoices('MARITAL_STATUS_CHOICES')
  ```

**Completed:** _____

---

### 2.5 Contact Types

- [ ] **Consolidate contact type definitions**
  ```python
  # Remove duplicate CONTACT_TYPE_CHOICES from:
  # - partner_onboarding/models.py:332-338
  # - partners/models.py:499-505
  # - partners/models.py:718-724
  
  # Use single source: ConfigurationService.get_choice_list('CONTACT_TYPE_CHOICES')
  ```

- [ ] **Update all models**
  ```python
  class ApplicationContact(models.Model):
      contact_type = models.CharField(max_length=50)  # Remove choices=
  ```

- [ ] **Update frontend**
  ```typescript
  const { data: contactTypes } = useChoices('CONTACT_TYPE_CHOICES')
  ```

**Completed:** _____

---

### 2.6 Currencies

- [ ] **Make default currency configurable**
  ```python
  # backend/apps/partner_onboarding/models.py:377
  
  # BEFORE
  currency = models.CharField(max_length=3, default="TZS")
  
  # AFTER
  from apps.system_parameters.services.config_service import ConfigurationService
  
  def get_default_currency():
      return ConfigurationService.get_parameter('DEFAULT_CURRENCY', 'TZS')
  
  class ApplicationBankAccount(models.Model):
      currency = models.CharField(max_length=3, default=get_default_currency)
  ```

- [ ] **Add currency choice list**
  ```python
  # Seed CURRENCY_CHOICES to ChoiceList in migration
  # Include: TZS, USD, EUR, GBP, etc.
  ```

**Completed:** _____

---

### 2.7 User Types & OTP Methods

- [ ] **Move UserType to ChoiceList**
  ```python
  # backend/apps/users/models.py:69-76
  
  # BEFORE
  class UserType(models.TextChoices):
      PORTAL_USER = 'PORTAL_USER', 'Portal User'
      MANAGER = 'MANAGER', 'Manager'
      # ...
  
  # AFTER - Remove TextChoices enum
  class User(AbstractUser):
      user_type = models.CharField(max_length=50)  # Validate against ChoiceList
  ```

- [ ] **Move OTPMethod to ChoiceList**
  ```python
  # backend/apps/users/models.py:78-81
  
  # BEFORE
  class OTPMethod(models.TextChoices):
      AUTH_APP = 'AUTH_APP', 'Authenticator App'
      SMS = 'SMS', 'SMS'
      EMAIL = 'EMAIL', 'Email'
  
  # AFTER - Remove enum, use ChoiceList
  ```

**Completed:** _____

---

### 2.8 Approval & Audit Statuses

- [ ] **Remove hardcoded approval statuses**
  ```python
  # backend/apps/governance/models.py:31-36
  
  # BEFORE
  APPROVAL_STATUS_CHOICES = [
      ("PENDING", "Pending"),
      ("APPROVED", "Approved"),
      ("REJECTED", "Rejected"),
      ("CANCELLED", "Cancelled")
  ]
  
  # AFTER - Use ChoiceList
  ```

- [ ] **Update approval service to use constants**
  ```python
  # backend/apps/governance/services/approval_service.py
  
  # BEFORE
  approval.status = "PENDING"
  
  # AFTER
  from apps.governance.constants import APPROVAL_STATUS
  
  approval.status = APPROVAL_STATUS.PENDING
  ```

**Completed:** _____

---

### 2.9 Dashboard Hardcoded Mappings

- [ ] **Make dashboard type mapping configurable**
  ```python
  # backend/apps/dashboard/views.py:128-133
  
  # BEFORE
  type_map = {
      'INDIVIDUAL': 'client',
      'CORPORATE': 'intermediary',
      'AGENT': 'serviceProvider',
      'BROKER': 'coInsurer'
  }
  
  # AFTER
  def get_dashboard_mapping():
      # Fetch from SystemParameter
      mapping = SystemParameter.objects.filter(
          group__code='DASHBOARD_CONFIG'
      ).first()
      
      if mapping:
          return json.loads(mapping.value)
      
      # Fallback to default
      return {
          'INDIVIDUAL': 'client',
          'CORPORATE': 'intermediary',
      }
  ```

**Completed:** _____

---

## 3. Onboarding Pipeline Fixes

### 3.1 Enable Multi-Role Selection During Ingestion

- [ ] **Update PartnerApplication model to support multiple types at creation**
  ```python
  # backend/apps/partner_onboarding/models.py
  
  # Keep partner_type field for backwards compatibility
  class PartnerApplication(models.Model):
      partner_type = models.CharField(max_length=50, blank=True)  # Make optional
      # partner_types M2M already exists via ApplicationPartnerType
  ```

- [ ] **Update ApplicationForm to allow multi-select**
  ```typescript
  // insurance-dashboard-ui/src/pages/onboarding/ApplicationForm.tsx
  
  import { useChoices } from '@/hooks/useChoices'
  
  export function ApplicationForm() {
    const { data: partnerTypes } = useChoices('PARTNER_TYPE_CHOICES')
    const [selectedTypes, setSelectedTypes] = useState<string[]>([])
    
    return (
      <div>
        <h3>Select Partner Roles</h3>
        {partnerTypes?.map(type => (
          <label key={type.value}>
            <input
              type="checkbox"
              value={type.value}
              checked={selectedTypes.includes(type.value)}
              onChange={(e) => {
                if (e.target.checked) {
                  setSelectedTypes([...selectedTypes, type.value])
                } else {
                  setSelectedTypes(selectedTypes.filter(t => t !== type.value))
                }
              }}
            />
            {type.label}
          </label>
        ))}
      </div>
    )
  }
  ```

- [ ] **Update backend to handle multiple partner types**
  ```python
  # backend/apps/partner_onboarding/serializers.py
  
  class PartnerApplicationSerializer(serializers.ModelSerializer):
      partner_types = serializers.ListField(
          child=serializers.CharField(),
          write_only=True,
          required=True
      )
      
      def create(self, validated_data):
          partner_types = validated_data.pop('partner_types')
          
          # Set first type as primary for backwards compatibility
          validated_data['partner_type'] = partner_types[0]
          
          application = PartnerApplication.objects.create(**validated_data)
          
          # Create ApplicationPartnerType records for all types
          from apps.partners.models import PartnerType
          for type_code in partner_types:
              partner_type = PartnerType.objects.get(code=type_code)
              ApplicationPartnerType.objects.create(
                  application=application,
                  partner_type=partner_type,
                  is_primary=(type_code == partner_types[0])
              )
          
          return application
  ```

**Completed:** _____

---

### 3.2 Bulk Upload Dynamic Validation

- [ ] **Refactor validators.py to use ConfigurationService**
  ```python
  # backend/apps/partner_onboarding/validators.py
  
  from apps.system_parameters.services.config_service import ConfigurationService
  from apps.system_parameters.services.validation_config_service import ValidationConfigService
  
  class BulkUploadValidator:
      def __init__(self, partner_type):
          self.partner_type = partner_type
          self.config_service = ConfigurationService()
          self.validation_service = ValidationConfigService()
      
      def get_expected_headers(self):
          """Fetch required headers from configuration"""
          required_fields = self.validation_service.get_required_fields(self.partner_type)
          return [field['name'] for field in required_fields]
      
      def get_required_fields(self):
          """Fetch required fields from configuration"""
          return self.validation_service.get_required_fields(self.partner_type)
      
      def validate_row(self, row, row_num):
          """Validate single row against dynamic rules"""
          errors = []
          required_fields = self.get_required_fields()
          choice_lists = self.config_service.get_all_choice_lists()
          
          for field in required_fields:
              field_name = field['name']
              value = row.get(field_name)
              
              # Check required
              if field['required'] and not value:
                  errors.append(f"Row {row_num}: {field_name} is required")
                  continue
              
              # Validate choice fields
              if field['type'] == 'choice' and value:
                  choice_list_code = field['choice_list_code']
                  valid_options = choice_lists.get(choice_list_code, [])
                  valid_values = [opt['value'] for opt in valid_options]
                  
                  if value not in valid_values:
                      errors.append(
                          f"Row {row_num}: Invalid {field_name}. "
                          f"Valid options: {valid_values}"
                      )
          
          return errors
      
      def validate_file(self, file_data):
          """Validate entire file"""
          errors = []
          
          # Validate headers
          expected_headers = self.get_expected_headers()
          actual_headers = list(file_data.columns)
          
          missing_headers = set(expected_headers) - set(actual_headers)
          if missing_headers:
              errors.append(f"Missing columns: {missing_headers}")
              return errors  # Can't proceed without headers
          
          # Validate rows
          for idx, row in file_data.iterrows():
              row_errors = self.validate_row(row.to_dict(), idx + 2)  # +2 for header and 0-index
              errors.extend(row_errors)
          
          return errors
  ```

- [ ] **Update bulk upload view to use dynamic validator**
  ```python
  # backend/apps/partner_onboarding/views.py
  
  @api_view(["POST"])
  def bulk_upload(request):
      if not request.user.is_authenticated:
          return Response({"error": "Authentication required"}, status=401)
      
      # Check permission
      if not request.user.has_module_permission('partner_onboarding', 'CREATE'):
          return Response({"error": "Permission denied"}, status=403)
      
      file = request.FILES.get('file')
      partner_type = request.data.get('partner_type')
      
      if not file or not partner_type:
          return Response({"error": "File and partner_type required"}, status=400)
      
      # Read file
      df = pd.read_excel(file)
      
      # Validate using dynamic validator
      validator = BulkUploadValidator(partner_type)
      errors = validator.validate_file(df)
      
      if errors:
          return Response({"errors": errors}, status=400)
      
      # Process valid rows
      created_applications = []
      for idx, row in df.iterrows():
          app = create_application_from_row(row, partner_type)
          created_applications.append(app.id)
      
      return Response({
          "message": f"Successfully created {len(created_applications)} applications",
          "application_ids": created_applications
      })
  ```

**Completed:** _____

---

### 3.3 Bulk Upload Creates ApplicationPartnerType Records

- [ ] **Update bulk upload to create M2M records**
  ```python
  # backend/apps/partner_onboarding/views.py
  
  def create_application_from_row(row, partner_type):
      """Create application and partner type assignments"""
      from apps.partners.models import PartnerType
      
      # Create application
      app = PartnerApplication.objects.create(
          partner_type=partner_type,
          # ... other fields from row
      )
      
      # Create ApplicationPartnerType record
      partner_type_obj = PartnerType.objects.get(code=partner_type)
      ApplicationPartnerType.objects.create(
          application=app,
          partner_type=partner_type_obj,
          is_primary=True
      )
      
      return app
  ```

**Completed:** _____

---

### 3.4 Conversion Carries Over All Data

- [ ] **Refactor convert_to_partner to preserve all data**
  ```python
  # backend/apps/partner_onboarding/services/application_service.py
  
  def convert_to_partner(self, application):
      """Convert application to partner, preserving all data"""
      from apps.partners.models import (
          Partner, IndividualProfile, CorporateProfile,
          PartnerTypeAssignment, PartnerContact, PartnerBankAccount,
          PartnerFieldValue
      )
      from apps.partners.services.setup_service import PartnerSetupService
      
      # Create partner
      partner = Partner.objects.create(
          partner_code=self.generate_partner_code(),
          status='ACTIVE',
          # ... basic fields
      )
      
      # Create profile
      if application.partner_type == 'INDIVIDUAL':
          IndividualProfile.objects.create(
              partner=partner,
              first_name=application.first_name,
              last_name=application.last_name,
              # ... map all individual fields
          )
      else:
          CorporateProfile.objects.create(
              partner=partner,
              company_name=application.company_name,
              # ... map all corporate fields
          )
      
      # Carry over partner type assignments
      for app_type in application.partner_types.all():
          PartnerTypeAssignment.objects.create(
              partner=partner,
              partner_type=app_type.partner_type,
              is_primary=app_type.is_primary
          )
      
      # Carry over contacts
      for contact in application.contacts.all():
          PartnerContact.objects.create(
              partner=partner,
              contact_type=contact.contact_type,
              full_name=contact.full_name,
              email=contact.email,
              phone=contact.phone,
              # ... all contact fields
          )
      
      # Carry over bank accounts
      for account in application.bank_accounts.all():
          PartnerBankAccount.objects.create(
              partner=partner,
              bank_name=account.bank_name,
              account_number=account.account_number,
              # ... all bank fields
          )
      
      # Carry over dynamic field values
      for field_value in application.field_values.all():
          PartnerFieldValue.objects.create(
              partner=partner,
              field_configuration=field_value.field_configuration,
              value=field_value.value
          )
      
      # Generate partner setup (documents, KYC, etc.)
      PartnerSetupService.generate_setup(partner)
      
      # Update application status
      application.status = 'CONVERTED'
      application.converted_partner_id = partner.id
      application.save()
      
      return partner
  ```

**Completed:** _____

---

### 3.5 Add Financial Profiling Step

- [ ] **Create FinancialProfile model**
  ```python
  # backend/apps/partner_onboarding/models.py
  
  class FinancialProfile(models.Model):
      application = models.OneToOneField(
          PartnerApplication,
          on_delete=models.CASCADE,
          related_name='financial_profile'
      )
      
      # Income & Capital
      annual_income = models.DecimalField(max_digits=15, decimal_places=2, null=True)
      net_worth = models.DecimalField(max_digits=15, decimal_places=2, null=True)
      capital_adequacy = models.DecimalField(max_digits=15, decimal_places=2, null=True)
      
      # Verification
      income_verified = models.BooleanField(default=False)
      income_verified_by = models.ForeignKey(
          'users.User',
          null=True,
          on_delete=models.SET_NULL,
          related_name='verified_income'
      )
      income_verified_at = models.DateTimeField(null=True)
      
      bank_verified = models.BooleanField(default=False)
      bank_verified_by = models.ForeignKey(
          'users.User',
          null=True,
          on_delete=models.SET_NULL,
          related_name='verified_banks'
      )
      bank_verified_at = models.DateTimeField(null=True)
      
      # Assessment
      financial_suitability_score = models.IntegerField(null=True)
      financial_suitability_status = models.CharField(max_length=50, default='PENDING')
      assessed_by = models.ForeignKey(
          'users.User',
          null=True,
          on_delete=models.SET_NULL
      )
      assessed_at = models.DateTimeField(null=True)
      
      created_at = models.DateTimeField(auto_now_add=True)
      updated_at = models.DateTimeField(auto_now=True)
  ```

- [ ] **Create FinancialProfilingService**
  ```python
  # backend/apps/partner_onboarding/services/financial_service.py
  
  class FinancialProfilingService:
      @staticmethod
      def create_profile(application):
          """Create financial profile for application"""
          profile, created = FinancialProfile.objects.get_or_create(
              application=application
          )
          return profile
      
      @staticmethod
      def assess_suitability(profile, assessed_by):
          """Assess financial suitability"""
          score = 0
          
          # Income assessment
          if profile.annual_income and profile.annual_income >= 10000000:  # 10M TZS
              score += 30
          elif profile.annual_income and profile.annual_income >= 5000000:
              score += 20
          
          # Net worth assessment
          if profile.net_worth and profile.net_worth >= 50000000:
              score += 30
          elif profile.net_worth and profile.net_worth >= 20000000:
              score += 20
          
          # Verification bonuses
          if profile.income_verified:
              score += 20
          if profile.bank_verified:
              score += 20
          
          profile.financial_suitability_score = score
          profile.financial_suitability_status = 'APPROVED' if score >= 60 else 'REJECTED'
          profile.assessed_by = assessed_by
          profile.assessed_at = timezone.now()
          profile.save()
          
          return profile
  ```

- [ ] **Add financial profiling API endpoints**
  ```python
  # backend/apps/partner_onboarding/views.py
  
  @api_view(['GET', 'POST'])
  def financial_profile(request, application_id):
      application = PartnerApplication.objects.get(id=application_id)
      
      if request.method == 'GET':
          profile = getattr(application, 'financial_profile', None)
          if not profile:
              profile = FinancialProfilingService.create_profile(application)
          return Response(FinancialProfileSerializer(profile).data)
      
      elif request.method == 'POST':
          # Check permission
          if not request.user.has_module_permission('finance', 'MANAGE'):
              return Response({"error": "Permission denied"}, status=403)
          
          profile = FinancialProfilingService.create_profile(application)
          serializer = FinancialProfileSerializer(profile, data=request.data)
          
          if serializer.is_valid():
              serializer.save()
              return Response(serializer.data)
          return Response(serializer.errors, status=400)
  
  @api_view(['POST'])
  def assess_financial_suitability(request, application_id):
      if not request.user.has_module_permission('finance', 'MANAGE'):
          return Response({"error": "Permission denied"}, status=403)
      
      application = PartnerApplication.objects.get(id=application_id)
      profile = application.financial_profile
      
      profile = FinancialProfilingService.assess_suitability(profile, request.user)
      
      return Response(FinancialProfileSerializer(profile).data)
  ```

- [ ] **Add financial profiling UI**
  ```typescript
  // insurance-dashboard-ui/src/pages/onboarding/FinancialProfiling.tsx
  
  export function FinancialProfiling({ applicationId }: { applicationId: number }) {
    const { data: profile, refetch } = useQuery(
      ['financial-profile', applicationId],
      () => api.get(`/api/v1/onboarding/applications/${applicationId}/financial-profile/`)
    )
    
    const assessMutation = useMutation(
      () => api.post(`/api/v1/onboarding/applications/${applicationId}/assess-financial/`),
      { onSuccess: () => refetch() }
    )
    
    return (
      <div>
        <h2>Financial Profiling</h2>
        
        <div>
          <label>Annual Income (TZS)</label>
          <input type="number" value={profile?.annual_income} />
        </div>
        
        <div>
          <label>Net Worth (TZS)</label>
          <input type="number" value={profile?.net_worth} />
        </div>
        
        <div>
          <label>
            <input type="checkbox" checked={profile?.income_verified} />
            Income Verified
          </label>
        </div>
        
        <button onClick={() => assessMutation.mutate()}>
          Assess Suitability
        </button>
        
        {profile?.financial_suitability_status && (
          <div>
            <h3>Assessment Result</h3>
            <p>Score: {profile.financial_suitability_score}</p>
            <p>Status: {profile.financial_suitability_status}</p>
          </div>
        )}
      </div>
    )
  }
  ```

- [ ] **Insert financial profiling in workflow**
  ```python
  # Update workflow engine configuration in SystemParameter
  
  # STATE_MACHINE should include:
  # UNDER_REVIEW -> COMPLIANCE_CHECK -> FINANCIAL_REVIEW -> PENDING_APPROVAL -> APPROVED
  ```

**Completed:** _____

---

### 3.6 Add Master Agent Assignment

- [ ] **Create MasterAgent model**
  ```python
  # backend/apps/partners/models.py
  
  class MasterAgent(models.Model):
      """Represents a master agent who supervises other agents"""
      partner = models.OneToOneField(
          Partner,
          on_delete=models.CASCADE,
          related_name='master_agent_profile'
      )
      
      agent_code = models.CharField(max_length=50, unique=True)
      region = models.CharField(max_length=100, blank=True)
      territory = models.CharField(max_length=100, blank=True)
      
      is_active = models.BooleanField(default=True)
      created_at = models.DateTimeField(auto_now_add=True)
      updated_at = models.DateTimeField(auto_now=True)
      
      def __str__(self):
          return f"Master Agent: {self.partner.full_name}"
  ```

- [ ] **Add master_agent FK to Partner model**
  ```python
  # backend/apps/partners/models.py
  
  class Partner(models.Model):
      # ... existing fields ...
      
      master_agent = models.ForeignKey(
          MasterAgent,
          null=True,
          blank=True,
          on_delete=models.SET_NULL,
          related_name='subordinate_agents'
      )
  ```

- [ ] **Add master_agent FK to PartnerApplication model**
  ```python
  # backend/apps/partner_onboarding/models.py
  
  class PartnerApplication(models.Model):
      # ... existing fields ...
      
      proposed_master_agent = models.ForeignKey(
          'partners.MasterAgent',
          null=True,
          blank=True,
          on_delete=models.SET_NULL,
          related_name='proposed_applications'
      )
  ```

- [ ] **Create MasterAgentAssignmentService**
  ```python
  # backend/apps/partners/services/master_agent_service.py
  
  class MasterAgentAssignmentService:
      @staticmethod
      def assign_master_agent(partner, master_agent, assigned_by):
          """Assign master agent to partner"""
          if not master_agent.is_active:
              raise ValidationError("Master agent is not active")
          
          # Check if master agent is already at capacity
          current_count = Partner.objects.filter(master_agent=master_agent).count()
          max_capacity = SystemParameter.objects.get(
              group__code='AGENCY_CONFIG',
              key='MAX_SUBORDINATES_PER_MASTER_AGENT'
          ).value
          
          if current_count >= int(max_capacity):
              raise ValidationError("Master agent has reached subordinate capacity")
          
          partner.master_agent = master_agent
          partner.save()
          
          # Create audit log
          AuditLog.objects.create(
              entity_type='partner',
              entity_id=partner.id,
              action='MASTER_AGENT_ASSIGNED',
              user=assigned_by,
              details=f"Assigned to master agent {master_agent.agent_code}"
          )
          
          return partner
      
      @staticmethod
      def remove_master_agent(partner, removed_by):
          """Remove master agent assignment"""
          old_master = partner.master_agent
          partner.master_agent = None
          partner.save()
          
          # Create audit log
          AuditLog.objects.create(
              entity_type='partner',
              entity_id=partner.id,
              action='MASTER_AGENT_REMOVED',
              user=removed_by,
              details=f"Removed from master agent {old_master.agent_code if old_master else 'None'}"
          )
          
          return partner
  ```

- [ ] **Add master agent assignment UI**
  ```typescript
  // insurance-dashboard-ui/src/pages/onboarding/MasterAgentAssignment.tsx
  
  export function MasterAgentAssignment({ applicationId }: { applicationId: number }) {
    const { data: masterAgents } = useQuery(
      ['master-agents'],
      () => api.get('/api/v1/partners/master-agents/')
    )
    
    const { data: application } = useQuery(
      ['application', applicationId],
      () => api.get(`/api/v1/onboarding/applications/${applicationId}/`)
    )
    
    const assignMutation = useMutation(
      (masterAgentId: number) => 
        api.post(`/api/v1/onboarding/applications/${applicationId}/assign-master-agent/`, {
          master_agent_id: masterAgentId
        })
    )
    
    return (
      <div>
        <h2>Master Agent Assignment</h2>
        
        {application?.partner_types?.includes('AGENT') && (
          <div>
            <label>Select Master Agent</label>
            <select
              value={application?.proposed_master_agent?.id || ''}
              onChange={(e) => assignMutation.mutate(Number(e.target.value))}
            >
              <option value="">No Master Agent</option>
              {masterAgents?.map(agent => (
                <option key={agent.id} value={agent.id}>
                  {agent.agent_code} - {agent.partner_name} ({agent.region})
                </option>
              ))}
            </select>
          </div>
        )}
        
        {application?.proposed_master_agent && (
          <div>
            <h3>Assigned Master Agent</h3>
            <p>Code: {application.proposed_master_agent.agent_code}</p>
            <p>Name: {application.proposed_master_agent.partner_name}</p>
            <p>Region: {application.proposed_master_agent.region}</p>
          </div>
        )}
      </div>
    )
  }
  ```

**Completed:** _____

---

## 4. RBAC Implementation

### 4.1 Seed Required Permissions

- [ ] **Create migration to seed all permissions**
  ```python
  # backend/apps/users/migrations/0004_seed_rbac_data.py
  
  from django.db import migrations
  
  def seed_permissions(apps, schema_editor):
      UserPermission = apps.get_model('users', 'UserPermission')
      
      permissions = [
          # System Parameters
          ('system_parameters', 'READ', 'View system parameters'),
          ('system_parameters', 'CREATE', 'Create system parameters'),
          ('system_parameters', 'UPDATE', 'Update system parameters'),
          ('system_parameters', 'DELETE', 'Delete system parameters'),
          ('system_parameters', 'MANAGE', 'Full management of system parameters'),
          
          # User Management
          ('users', 'READ', 'View users'),
          ('users', 'CREATE', 'Create users'),
          ('users', 'UPDATE', 'Update users'),
          ('users', 'DELETE', 'Delete users'),
          ('users', 'MANAGE', 'Full management of users'),
          
          # Partner Onboarding
          ('partner_onboarding', 'READ', 'View applications'),
          ('partner_onboarding', 'CREATE', 'Create applications'),
          ('partner_onboarding', 'UPDATE', 'Update applications'),
          ('partner_onboarding', 'DELETE', 'Delete applications'),
          ('partner_onboarding', 'REVIEW', 'Review applications'),
          ('partner_onboarding', 'APPROVE', 'Approve/reject applications'),
          ('partner_onboarding', 'COMPLIANCE', 'Perform compliance checks'),
          ('partner_onboarding', 'CONVERT', 'Convert applications to partners'),
          ('partner_onboarding', 'BULK_IMPORT', 'Bulk import applications'),
          
          # Partner Management
          ('partners', 'READ', 'View partners'),
          ('partners', 'CREATE', 'Create partners'),
          ('partners', 'UPDATE', 'Update partners'),
          ('partners', 'DELETE', 'Delete partners'),
          ('partners', 'SUSPEND', 'Suspend partners'),
          ('partners', 'MANAGE', 'Full management of partners'),
          
          # Partner Configuration
          ('partner_config', 'READ', 'View partner configuration'),
          ('partner_config', 'CREATE', 'Create partner configuration'),
          ('partner_config', 'UPDATE', 'Update partner configuration'),
          ('partner_config', 'DELETE', 'Delete partner configuration'),
          ('partner_config', 'MANAGE', 'Full management of partner configuration'),
          
          # Governance
          ('governance', 'READ', 'View approvals'),
          ('governance', 'APPROVE', 'Approve/reject requests'),
          ('governance', 'MANAGE', 'Full management of governance'),
          
          # Finance
          ('finance', 'READ', 'View financial profiles'),
          ('finance', 'UPDATE', 'Update financial profiles'),
          ('finance', 'ASSESS', 'Assess financial suitability'),
          ('finance', 'MANAGE', 'Full management of finance'),
          
          # Reports
          ('reports', 'READ', 'View reports'),
          ('reports', 'EXPORT', 'Export reports'),
          
          # Audit
          ('audit', 'READ', 'View audit logs'),
          ('audit', 'EXPORT', 'Export audit logs'),
      ]
      
      for module, action, description in permissions:
          UserPermission.objects.get_or_create(
              module=module,
              action=action,
              defaults={'description': description}
          )
  
  class Migration(migrations.Migration):
      dependencies = [
          ('users', '0003_...'),
      ]
      
      operations = [
          migrations.RunPython(seed_permissions),
      ]
  ```

**Completed:** _____

---

### 4.2 Seed Required User Groups (Roles)

- [ ] **Create migration to seed user groups**
  ```python
  # backend/apps/users/migrations/0005_seed_user_groups.py
  
  from django.db import migrations
  
  def seed_user_groups(apps, schema_editor):
      UserGroup = apps.get_model('users', 'UserGroup')
      UserPermission = apps.get_model('users', 'UserPermission')
      
      # System Administrator
      sys_admin, _ = UserGroup.objects.get_or_create(
          name='System Administrator',
          group_name='system_admin'
      )
      sys_admin.permissions.set(UserPermission.objects.filter(
          module__in=['system_parameters', 'users', 'partner_config', 'governance', 'audit']
      ))
      
      # Onboarding Clerk
      clerk, _ = UserGroup.objects.get_or_create(
          name='Onboarding Clerk',
          group_name='onboarding_clerk'
      )
      clerk.permissions.set(UserPermission.objects.filter(
          module='partner_onboarding',
          action__in=['READ', 'CREATE', 'UPDATE', 'BULK_IMPORT']
      ))
      
      # Compliance Officer
      compliance, _ = UserGroup.objects.get_or_create(
          name='Compliance Officer',
          group_name='compliance_officer'
      )
      compliance.permissions.set(UserPermission.objects.filter(
          module='partner_onboarding',
          action__in=['READ', 'REVIEW', 'COMPLIANCE', 'APPROVE']
      ))
      
      # Finance Manager
      finance, _ = UserGroup.objects.get_or_create(
          name='Finance Manager',
          group_name='finance_manager'
      )
      finance.permissions.set(UserPermission.objects.filter(
          module__in=['finance', 'partner_onboarding']
      ).filter(
          models.Q(module='finance') | 
          models.Q(module='partner_onboarding', action__in=['READ', 'APPROVE'])
      ))
      
      # ZIC Auditor
      auditor, _ = UserGroup.objects.get_or_create(
          name='ZIC Auditor',
          group_name='zic_auditor'
      )
      auditor.permissions.set(UserPermission.objects.filter(
          module__in=['governance', 'audit', 'reports', 'partner_onboarding', 'partners']
      ).filter(
          models.Q(module__in=['governance', 'audit', 'reports'], action__in=['READ', 'EXPORT']) |
          models.Q(module__in=['partner_onboarding', 'partners'], action='READ')
      ))
  
  class Migration(migrations.Migration):
      dependencies = [
          ('users', '0004_seed_rbac_data'),
      ]
      
      operations = [
          migrations.RunPython(seed_user_groups),
      ]
  ```

**Completed:** _____

---

### 4.3 Update Login Response to Include Permissions

- [ ] **Update authentication views**
  ```python
  # backend/apps/authentication/views.py
  
  @api_view(['POST'])
  def login(request):
      # ... existing authentication logic ...
      
      user = authenticate(username=username, password=password)
      
      if user:
          token, created = Token.objects.get_or_create(user=user)
          
          # Get user permissions
          permissions = user.get_all_permissions()
          permission_list = [
              {'module': module, 'action': action}
              for module, action in permissions
          ]
          
          # Get user groups
          groups = list(user.groups.values_list('name', flat=True))
          
          return Response({
              'token': token.key,
              'user': {
                  'id': user.id,
                  'username': user.username,
                  'email': user.email,
                  'user_type': user.user_type,
                  'permissions': permission_list,
                  'groups': groups,
                  'is_active': user.is_active,
              }
          })
  ```

- [ ] **Create /me/ endpoint for refreshing user data**
  ```python
  # backend/apps/authentication/views.py
  
  @api_view(['GET'])
  @permission_classes([IsAuthenticated])
  def me(request):
      """Get current user info with permissions"""
      user = request.user
      
      permissions = user.get_all_permissions()
      permission_list = [
          {'module': module, 'action': action}
          for module, action in permissions
      ]
      
      groups = list(user.groups.values_list('name', flat=True))
      
      return Response({
          'user': {
              'id': user.id,
              'username': user.username,
              'email': user.email,
              'user_type': user.user_type,
              'permissions': permission_list,
              'groups': groups,
              'is_active': user.is_active,
          }
      })
  ```

- [ ] **Add URL route**
  ```python
  # backend/apps/authentication/urls.py
  
  urlpatterns = [
      path('login/', views.login, name='login'),
      path('me/', views.me, name='me'),
  ]
  ```

**Completed:** _____

---

### 4.4 Protect Onboarding Endpoints

- [ ] **Update onboarding permissions to check user authority**
  ```python
  # backend/apps/partner_onboarding/permissions.py
  
  from rest_framework import permissions
  
  class CanReviewApplication(permissions.BasePermission):
      def has_object_permission(self, request, view, obj):
          # Check both status AND user permission
          return (
              obj.status in ("SUBMITTED", "UNDER_REVIEW", "PENDING_DOCUMENTS")
              and request.user.has_module_permission('partner_onboarding', 'REVIEW')
          )
  
  class CanPerformComplianceAction(permissions.BasePermission):
      def has_object_permission(self, request, view, obj):
          return (
              obj.status in ("COMPLIANCE_CHECK", "SUSPENDED")
              and request.user.has_module_permission('partner_onboarding', 'COMPLIANCE')
          )
  
  class CanApproveApplication(permissions.BasePermission):
      def has_object_permission(self, request, view, obj):
          return (
              obj.status in ("FINANCIAL_REVIEW", "PENDING_APPROVAL")
              and request.user.has_module_permission('partner_onboarding', 'APPROVE')
          )
  
  class CanRejectApplication(permissions.BasePermission):
      def has_object_permission(self, request, view, obj):
          return (
              obj.status in ("SUBMITTED", "UNDER_REVIEW", "COMPLIANCE_CHECK", "PENDING_APPROVAL")
              and request.user.has_module_permission('partner_onboarding', 'APPROVE')
          )
  
  class CanConvertApplication(permissions.BasePermission):
      def has_object_permission(self, request, view, obj):
          return (
              obj.status == "APPROVED"
              and request.user.has_module_permission('partner_onboarding', 'CONVERT')
          )
  ```

- [ ] **Update onboarding views to use new permissions**
  ```python
  # backend/apps/partner_onboarding/views.py
  
  class PartnerApplicationViewSet(viewsets.ModelViewSet):
      queryset = PartnerApplication.objects.all()
      serializer_class = PartnerApplicationSerializer
      
      def get_permissions(self):
          if self.action in ['list', 'retrieve']:
              return [permissions.IsAuthenticated()]
          elif self.action == 'create':
              return [permissions.IsAuthenticated(), HasModulePermission()]
          elif self.action == 'review':
              return [permissions.IsAuthenticated(), CanReviewApplication()]
          elif self.action == 'compliance_check':
              return [permissions.IsAuthenticated(), CanPerformComplianceAction()]
          elif self.action in ['approve', 'reject']:
              return [permissions.IsAuthenticated(), CanApproveApplication()]
          elif self.action == 'convert':
              return [permissions.IsAuthenticated(), CanConvertApplication()]
          return [permissions.IsAuthenticated(), HasModulePermission()]
  ```

**Completed:** _____

---

### 4.5 Protect Governance Approval Endpoints

- [ ] **Add permission checks to approval actions**
  ```python
  # backend/apps/governance/views.py
  
  class ApprovalRequestViewSet(viewsets.ModelViewSet):
      queryset = ApprovalRequest.objects.all()
      serializer_class = ApprovalRequestSerializer
      module_code = 'governance'
      
      def get_permissions(self):
          if self.action in ['list', 'retrieve']:
              return [permissions.IsAuthenticated()]
          elif self.action in ['approve', 'reject', 'cancel']:
              return [permissions.IsAuthenticated(), HasModulePermission()]
          return [permissions.IsAuthenticated(), HasModulePermission()]
      
      @action(detail=True, methods=['post'])
      def approve(self, request, pk=None):
          approval = self.get_object()
          comments = request.data.get('comments', '')
          
          ApprovalService.approve(
              approval_id=approval.id,
              approved_by=request.user,
              comments=comments
          )
          
          return Response({'status': 'approved'})
      
      @action(detail=True, methods=['post'])
      def reject(self, request, pk=None):
          approval = self.get_object()
          comments = request.data.get('comments', '')
          
          ApprovalService.reject(
              approval_id=approval.id,
              approved_by=request.user,
              comments=comments
          )
          
          return Response({'status': 'rejected'})
  ```

**Completed:** _____

---

### 4.6 Fix PermissionGroup Integration

- [ ] **Update UserGroup to use PermissionGroup**
  ```python
  # backend/apps/users/models.py
  
  class UserGroup(models.Model):
      name = models.CharField(max_length=100)
      group_name = models.CharField(max_length=50, unique=True)
      
      # Link to PermissionGroup instead of direct UserPermission
      permission_groups = models.ManyToManyField(
          'PermissionGroup',
          related_name='user_groups',
          blank=True
      )
      
      # Keep direct permissions for flexibility
      permissions = models.ManyToManyField(
          UserPermission,
          related_name='groups',
          blank=True
      )
      
      def get_all_permissions(self):
          """Get all permissions from both direct and permission groups"""
          direct_perms = set(self.permissions.values_list('module', 'action'))
          
          group_perms = set(
              self.permission_groups.values_list(
                  'permissions__module',
                  'permissions__action'
              )
          )
          
          return direct_perms.union(group_perms)
  ```

- [ ] **Update User.has_module_permission**
  ```python
  # backend/apps/users/models.py
  
  class User(AbstractUser):
      def has_module_permission(self, module_code, action='READ'):
          if self.is_superuser:
              return True
          
          # Check direct permissions via groups
          has_direct = self.groups.filter(
              permissions__module=module_code,
              permissions__action=action,
              permissions__is_active=True
          ).exists()
          
          if has_direct:
              return True
          
          # Check via permission groups
          has_via_group = self.groups.filter(
              permission_groups__permissions__module=module_code,
              permission_groups__permissions__action=action,
              permission_groups__permissions__is_active=True
          ).exists()
          
          return has_via_group
  ```

**Completed:** _____

---

## 5. Database Seeding Requirements

### 5.1 Seed Partner Types

- [ ] **Create migration to seed partner types**
  ```python
  # backend/apps/partners/migrations/0002_seed_partner_types.py
  
  from django.db import migrations
  
  def seed_partner_types(apps, schema_editor):
      PartnerType = apps.get_model('partners', 'PartnerType')
      
      types = [
          ('INDIVIDUAL', 'Individual', 'Individual partner (client)'),
          ('CORPORATE', 'Corporate', 'Corporate entity'),
          ('AGENT', 'Agent', 'Insurance agent'),
          ('BROKER', 'Broker', 'Insurance broker'),
          ('BANCASSURER', 'Bancassurer', 'Bank insurance partner'),
          ('SERVICE_PROVIDER', 'Service Provider', 'Service provider'),
      ]
      
      for code, name, description in types:
          PartnerType.objects.get_or_create(
              code=code,
              defaults={
                  'name': name,
                  'description': description,
                  'is_active': True,
              }
          )
  
  class Migration(migrations.Migration):
      dependencies = [
          ('partners', '0001_initial'),
      ]
      
      operations = [
          migrations.RunPython(seed_partner_types),
      ]
  ```

**Completed:** _____

---

### 5.2 Seed Choice Lists

- [ ] **Create migration to seed all choice lists**
  ```python
  # backend/apps/system_parameters/migrations/0002_seed_choice_lists.py
  
  from django.db import migrations
  
  def seed_choice_lists(apps, schema_editor):
      ChoiceList = apps.get_model('system_parameters', 'ChoiceList')
      ChoiceOption = apps.get_model('system_parameters', 'ChoiceOption')
      
      choice_lists_data = {
          'PARTNER_TYPE_CHOICES': [
              ('INDIVIDUAL', 'Individual', 1),
              ('CORPORATE', 'Corporate', 2),
              ('AGENT', 'Agent', 3),
              ('BROKER', 'Broker', 4),
              ('BANCASSURER', 'Bancassurer', 5),
              ('SERVICE_PROVIDER', 'Service Provider', 6),
          ],
          'APPLICATION_STATUS_CHOICES': [
              ('DRAFT', 'Draft', 1),
              ('SUBMITTED', 'Submitted', 2),
              ('UNDER_REVIEW', 'Under Review', 3),
              ('PENDING_DOCUMENTS', 'Pending Documents', 4),
              ('COMPLIANCE_CHECK', 'Compliance Check', 5),
              ('FINANCIAL_REVIEW', 'Financial Review', 6),
              ('PENDING_APPROVAL', 'Pending Approval', 7),
              ('APPROVED', 'Approved', 8),
              ('REJECTED', 'Rejected', 9),
              ('CONVERTED', 'Converted', 10),
              ('SUSPENDED', 'Suspended', 11),
          ],
          'GENDER_CHOICES': [
              ('MALE', 'Male', 1),
              ('FEMALE', 'Female', 2),
              ('OTHER', 'Other', 3),
          ],
          'TITLE_CHOICES': [
              ('MR', 'Mr', 1),
              ('MRS', 'Mrs', 2),
              ('MS', 'Ms', 3),
              ('DR', 'Dr', 4),
              ('PROF', 'Prof', 5),
          ],
          'NATIONALITY_CHOICES': [
              ('TANZANIAN', 'Tanzanian', 1),
              ('KENYAN', 'Kenyan', 2),
              ('UGANDAN', 'Ugandan', 3),
              ('RWANDAN', 'Rwandan', 4),
              ('BURUNDIAN', 'Burundian', 5),
              ('OTHER', 'Other', 6),
          ],
          'INDUSTRY_CHOICES': [
              ('AGRICULTURE', 'Agriculture', 1),
              ('BANKING', 'Banking & Finance', 2),
              ('CONSTRUCTION', 'Construction', 3),
              ('EDUCATION', 'Education', 4),
              ('HEALTHCARE', 'Healthcare', 5),
              ('IT', 'Information Technology', 6),
              ('INSURANCE', 'Insurance', 7),
              ('MANUFACTURING', 'Manufacturing', 8),
              ('TOURISM', 'Tourism & Hospitality', 9),
              ('GOVERNMENT', 'Government', 10),
              ('OTHER', 'Other', 11),
          ],
          'DOCUMENT_TYPE_CHOICES': [
              ('NATIONAL_ID', 'National ID', 1),
              ('PASSPORT', 'Passport', 2),
              ('DRIVERS_LICENSE', 'Driver\'s License', 3),
              ('VOTER_ID', 'Voter ID', 4),
              ('BIRTH_CERTIFICATE', 'Birth Certificate', 5),
              ('CERTIFICATE_OF_INCORPORATION', 'Certificate of Incorporation', 6),
              ('MEMORANDUM_OF_ARTICLES', 'Memorandum & Articles', 7),
              ('TAX_CLEARANCE', 'Tax Clearance Certificate', 8),
              ('FINANCIAL_STATEMENTS', 'Financial Statements', 9),
              ('BANK_STATEMENT', 'Bank Statement', 10),
              ('UTILITY_BILL', 'Utility Bill', 11),
              ('LICENSE', 'License/Certification', 12),
          ],
          'CONTACT_TYPE_CHOICES': [
              ('PRIMARY', 'Primary', 1),
              ('SECONDARY', 'Secondary', 2),
              ('BILLING', 'Billing', 3),
              ('TECHNICAL', 'Technical', 4),
              ('COMPLIANCE_OFFICER', 'Compliance Officer', 5),
              ('OTHER', 'Other', 6),
          ],
          'KYC_STATUS_CHOICES': [
              ('NOT_SET', 'Not Set', 1),
              ('PENDING_REVIEW', 'Pending Review', 2),
              ('VERIFIED', 'Verified', 3),
              ('REJECTED', 'Rejected', 4),
              ('EXPIRED', 'Expired', 5),
          ],
          'CURRENCY_CHOICES': [
              ('TZS', 'Tanzanian Shilling', 1),
              ('USD', 'US Dollar', 2),
              ('EUR', 'Euro', 3),
              ('GBP', 'British Pound', 4),
              ('KES', 'Kenyan Shilling', 5),
          ],
      }
      
      for list_code, options in choice_lists_data.items():
          choice_list, _ = ChoiceList.objects.get_or_create(
              code=list_code,
              defaults={
                  'name': list_code.replace('_', ' ').title(),
                  'is_active': True,
              }
          )
          
          for value, label, order in options:
              ChoiceOption.objects.get_or_create(
                  choice_list=choice_list,
                  value=value,
                  defaults={
                      'label': label,
                      'display_order': order,
                      'is_active': True,
                  }
              )
  
  class Migration(migrations.Migration):
      dependencies = [
          ('system_parameters', '0001_initial'),
      ]
      
      operations = [
          migrations.RunPython(seed_choice_lists),
      ]
  ```

**Completed:** _____

---

### 5.3 Seed System Parameters

- [ ] **Create migration to seed system parameters**
  ```python
  # backend/apps/system_parameters/migrations/0003_seed_system_parameters.py
  
  from django.db import migrations
  import json
  
  def seed_system_parameters(apps, schema_editor):
      SystemParameter = apps.get_model('system_parameters', 'SystemParameter')
      ParameterGroup = apps.get_model('system_parameters', 'ParameterGroup')
      
      # Create parameter groups
      system_group, _ = ParameterGroup.objects.get_or_create(
          code='SYSTEM_CONFIG',
          defaults={'name': 'System Configuration'}
      )
      
      dashboard_group, _ = ParameterGroup.objects.get_or_create(
          code='DASHBOARD_CONFIG',
          defaults={'name': 'Dashboard Configuration'}
      )
      
      agency_group, _ = ParameterGroup.objects.get_or_create(
          code='AGENCY_CONFIG',
          defaults={'name': 'Agency Configuration'}
      )
      
      # System parameters
      SystemParameter.objects.get_or_create(
          group=system_group,
          key='DEFAULT_CURRENCY',
          defaults={
              'value': 'TZS',
              'description': 'Default operational currency',
              'data_type': 'STRING',
          }
      )
      
      SystemParameter.objects.get_or_create(
          group=dashboard_group,
          key='PARTNER_TYPE_MAPPING',
          defaults={
              'value': json.dumps({
                  'INDIVIDUAL': 'client',
                  'CORPORATE': 'intermediary',
                  'AGENT': 'serviceProvider',
                  'BROKER': 'coInsurer',
              }),
              'description': 'Mapping of partner types to dashboard categories',
              'data_type': 'JSON',
          }
      )
      
      SystemParameter.objects.get_or_create(
          group=agency_group,
          key='MAX_SUBORDINATES_PER_MASTER_AGENT',
          defaults={
              'value': '50',
              'description': 'Maximum number of subordinate agents per master agent',
              'data_type': 'INTEGER',
          }
      )
  
  class Migration(migrations.Migration):
      dependencies = [
          ('system_parameters', '0002_seed_choice_lists'),
      ]
      
      operations = [
          migrations.RunPython(seed_system_parameters),
      ]
  ```

**Completed:** _____

---

## 6. Frontend Integration

### 6.1 Create useChoices Hook

- [ ] **Implement useChoices hook**
  ```typescript
  // insurance-dashboard-ui/src/hooks/useChoices.ts
  
  import { useQuery } from '@tanstack/react-query'
  import { api } from '@/lib/api'
  
  export interface ChoiceOption {
    value: string
    label: string
    description?: string
    is_active: boolean
  }
  
  export function useChoices(listCode: string) {
    return useQuery({
      queryKey: ['choices', listCode],
      queryFn: async () => {
        const response = await api.get(
          `/api/v1/system/choices/${listCode}/options/`
        )
        return response.data.options as ChoiceOption[]
      },
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
    })
  }
  
  export function useMultipleChoices(listCodes: string[]) {
    return useQuery({
      queryKey: ['choices', 'multiple', listCodes],
      queryFn: async () => {
        const promises = listCodes.map(code =>
          api.get(`/api/v1/system/choices/${code}/options/`)
        )
        const responses = await Promise.all(promises)
        
        const result: Record<string, ChoiceOption[]> = {}
        responses.forEach((response, index) => {
          result[listCodes[index]] = response.data.options
        })
        
        return result
      },
      staleTime: 5 * 60 * 1000,
    })
  }
  ```

**Completed:** _____

---

### 6.2 Update AuthUser Type

- [ ] **Add permissions to AuthUser**
  ```typescript
  // insurance-dashboard-ui/src/lib/types.ts
  
  export interface AuthUser {
    id: number
    username: string
    email: string
    userType: string
    permissions: Array<{ module: string; action: string }>
    groups: string[]
    is_active: boolean
  }
  ```

**Completed:** _____

---

### 6.3 Update useAuth Hook

- [ ] **Fetch permissions on login**
  ```typescript
  // insurance-dashboard-ui/src/hooks/useAuth.ts
  
  import { useState, useEffect } from 'react'
  import { api } from '@/lib/api'
  import { AuthUser } from '@/lib/types'
  
  export function useAuth() {
    const [user, setUser] = useState<AuthUser | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [accessToken, setAccessToken] = useState<string | null>(
      localStorage.getItem('accessToken')
    )
    
    useEffect(() => {
      if (accessToken) {
        api.get('/api/v1/auth/me/')
          .then(response => {
            setUser({
              ...response.data.user,
              permissions: response.data.user.permissions || [],
              groups: response.data.user.groups || [],
            })
          })
          .catch(() => {
            localStorage.removeItem('accessToken')
            setAccessToken(null)
            setUser(null)
          })
          .finally(() => setIsLoading(false))
      } else {
        setIsLoading(false)
      }
    }, [accessToken])
    
    const login = async (username: string, password: string) => {
      const response = await api.post('/api/v1/auth/login/', {
        username,
        password,
      })
      
      localStorage.setItem('accessToken', response.data.token)
      setAccessToken(response.data.token)
      setUser({
        ...response.data.user,
        permissions: response.data.user.permissions || [],
        groups: response.data.user.groups || [],
      })
      
      return response.data
    }
    
    const logout = () => {
      localStorage.removeItem('accessToken')
      setAccessToken(null)
      setUser(null)
    }
    
    const hasPermission = (module: string, action: string) => {
      return user?.permissions?.some(p => 
        p.module === module && p.action === action
      ) || false
    }
    
    return {
      user,
      isLoading,
      accessToken,
      login,
      logout,
      hasPermission,
    }
  }
  ```

**Completed:** _____

---

### 6.4 Update Sidebar with Permission Filtering

- [ ] **Filter navigation based on permissions**
  ```typescript
  // insurance-dashboard-ui/src/components/layout/Sidebar.tsx
  
  import { useAuth } from '@/hooks/useAuth'
  
  interface NavItem {
    label: string
    icon: any
    path?: string
    permission?: { module: string; action: string }
    children?: NavItem[]
  }
  
  const ALL_NAV_ITEMS: NavItem[] = [
    { label: "Dashboard", icon: LayoutDashboard, path: "/" },
    { 
      label: "System Parameters", 
      icon: Settings, 
      path: "/system-parameters",
      permission: { module: "system_parameters", action: "MANAGE" }
    },
    { 
      label: "User Management", 
      icon: UserCog, 
      path: "/users",
      permission: { module: "users", action: "MANAGE" }
    },
    { 
      label: "Onboarding", 
      icon: UserPlus, 
      path: "/onboarding",
      permission: { module: "partner_onboarding", action: "READ" }
    },
    { 
      label: "Partners", 
      icon: Users, 
      path: "/partners",
      permission: { module: "partners", action: "READ" }
    },
    { 
      label: "Approvals", 
      icon: CheckSquare, 
      path: "/approvals",
      permission: { module: "governance", action: "APPROVE" }
    },
    { 
      label: "Reports", 
      icon: FileText, 
      path: "/reports",
      permission: { module: "reports", action: "READ" }
    },
    { 
      label: "Audit Logs", 
      icon: Shield, 
      path: "/audit",
      permission: { module: "audit", action: "READ" }
    },
  ]
  
  export function Sidebar() {
    const { hasPermission } = useAuth()
    
    const navItems = ALL_NAV_ITEMS.filter(item => {
      if (!item.permission) return true
      
      return hasPermission(item.permission.module, item.permission.action)
    })
    
    return (
      <aside>
        {navItems.map(item => (
          <NavItem key={item.label} {...item} />
        ))}
      </aside>
    )
  }
  ```

**Completed:** _____

---

### 6.5 Create Permission Utility

- [ ] **Create permission helper functions**
  ```typescript
  // insurance-dashboard-ui/src/utils/permissions.ts
  
  export const PERMISSIONS = {
    SYSTEM_PARAMETERS: {
      READ: { module: 'system_parameters', action: 'READ' },
      MANAGE: { module: 'system_parameters', action: 'MANAGE' },
    },
    USERS: {
      READ: { module: 'users', action: 'READ' },
      MANAGE: { module: 'users', action: 'MANAGE' },
    },
    PARTNER_ONBOARDING: {
      READ: { module: 'partner_onboarding', action: 'READ' },
      CREATE: { module: 'partner_onboarding', action: 'CREATE' },
      REVIEW: { module: 'partner_onboarding', action: 'REVIEW' },
      APPROVE: { module: 'partner_onboarding', action: 'APPROVE' },
      COMPLIANCE: { module: 'partner_onboarding', action: 'COMPLIANCE' },
      CONVERT: { module: 'partner_onboarding', action: 'CONVERT' },
    },
    PARTNERS: {
      READ: { module: 'partners', action: 'READ' },
      MANAGE: { module: 'partners', action: 'MANAGE' },
    },
    GOVERNANCE: {
      APPROVE: { module: 'governance', action: 'APPROVE' },
    },
    FINANCE: {
      MANAGE: { module: 'finance', action: 'MANAGE' },
    },
  } as const
  
  export function permissionString(perm: { module: string; action: string }) {
    return `${perm.module}:${perm.action}`
  }
  ```

**Completed:** _____

---

## 7. Testing & Validation

### 7.1 Test Dynamic Partner Types

- [ ] **Add new partner type via admin**
  - Login as System Administrator
  - Navigate to System Parameters → Choice Lists → PARTNER_TYPE_CHOICES
  - Add new option: "REINSURER" / "Reinsurer"
  - Save

- [ ] **Verify new type appears in UI**
  - Navigate to Onboarding → Create Application
  - Verify "Reinsurer" appears in partner type dropdown
  - Create application with "Reinsurer" type
  - Verify it saves successfully

- [ ] **Verify filters include new type**
  - Navigate to Onboarding List
  - Check partner type filter
  - Verify "Reinsurer" appears

**Completed:** _____

---

### 7.2 Test Role-Conditional Documents

- [ ] **Configure document requirements**
  - Navigate to Partner Configuration → Document Requirements
  - For INDIVIDUAL: Require NATIONAL_ID, PASSPORT
  - For AGENT: Require LICENSE, NATIONAL_ID
  - Save

- [ ] **Test single role**
  - Create application with INDIVIDUAL role
  - Navigate to document upload
  - Verify only NATIONAL_ID and PASSPORT shown

- [ ] **Test multiple roles**
  - Add AGENT role to same application
  - Refresh document upload
  - Verify NATIONAL_ID, PASSPORT, and LICENSE shown
  - Verify NATIONAL_ID marked as mandatory (required by both)

**Completed:** _____

---

### 7.3 Test Approval Workflow

- [ ] **Submit application for approval**
  - Login as Onboarding Clerk
  - Create and submit application
  - Verify status changes to PENDING_APPROVAL
  - Verify ApprovalRequest created in governance module

- [ ] **Approve application**
  - Login as Compliance Officer
  - Navigate to Approvals
  - Find pending approval
  - Approve with comments
  - Verify application status changes to APPROVED

- [ ] **Test rejection**
  - Submit another application
  - Login as Compliance Officer
  - Reject with comments
  - Verify application status changes to REJECTED

**Completed:** _____

---

### 7.4 Test RBAC Enforcement

- [ ] **Test route protection**
  - Login as Onboarding Clerk
  - Attempt to navigate to /system-parameters
  - Verify redirected to /unauthorized
  - Attempt to navigate to /users
  - Verify redirected to /unauthorized

- [ ] **Test API protection**
  - Login as Onboarding Clerk
  - Attempt to POST to /api/v1/system/parameters/
  - Verify 403 Forbidden response
  - Attempt to POST to /api/v1/users/
  - Verify 403 Forbidden response

- [ ] **Test permission-based actions**
  - Login as Onboarding Clerk
  - Verify can create applications
  - Verify cannot approve applications
  - Login as Compliance Officer
  - Verify can approve applications

**Completed:** _____

---

### 7.5 Test Bulk Upload

- [ ] **Upload with dynamic validation**
  - Add new required field to INDIVIDUAL configuration
  - Upload CSV without new field
  - Verify validation error mentions missing field
  - Upload CSV with new field
  - Verify successful import

- [ ] **Test with new partner type**
  - Add REINSURER partner type
  - Configure required fields for REINSURER
  - Upload CSV with REINSURER data
  - Verify validation uses REINSURER configuration

**Completed:** _____

---

### 7.6 Test Financial Profiling

- [ ] **Create financial profile**
  - Navigate to application in COMPLIANCE_CHECK status
  - Click "Financial Profiling" tab
  - Enter income and net worth
  - Save

- [ ] **Assess suitability**
  - Login as Finance Manager
  - Open financial profile
  - Click "Assess Suitability"
  - Verify score calculated
  - Verify status set to APPROVED or REJECTED

- [ ] **Verify workflow progression**
  - Verify application can move to PENDING_APPROVAL after financial assessment

**Completed:** _____

---

### 7.7 Test Master Agent Assignment

- [ ] **Create master agent**
  - Navigate to Partners → Master Agents
  - Create new master agent
  - Set region and territory

- [ ] **Assign to application**
  - Create AGENT application
  - Navigate to Master Agent Assignment
  - Select master agent
  - Save

- [ ] **Verify conversion carries over**
  - Approve and convert application
  - Verify partner record has master_agent FK set

**Completed:** _____

---

### 7.8 Test Data Conversion

- [ ] **Convert application to partner**
  - Create application with multiple roles
  - Add contacts, bank accounts, documents
  - Fill all dynamic fields
  - Approve application
  - Convert to partner

- [ ] **Verify all data carried over**
  - Open partner record
  - Verify all partner types assigned
  - Verify all contacts present
  - Verify all bank accounts present
  - Verify all field values present
  - Verify document slots generated

**Completed:** _____

---

## Summary Checklist

### Critical Blockers (7 items)
- [ ] 1.1 Remove database constraint on partner_type
- [ ] 1.2 Route approvals through governance module
- [ ] 1.3 Implement role-conditional document upload
- [ ] 1.4 Protect system parameters endpoints
- [ ] 1.5 Fix KYC status mismatch
- [ ] 1.6 Implement permission-based route guards
- [ ] 1.7 Protect partner configuration endpoints

### Hardcoded Parameters (9 sections)
- [ ] 2.1 Partner types & categories
- [ ] 2.2 Application statuses
- [ ] 2.3 Document types
- [ ] 2.4 Demographic choices
- [ ] 2.5 Contact types
- [ ] 2.6 Currencies
- [ ] 2.7 User types & OTP methods
- [ ] 2.8 Approval & audit statuses
- [ ] 2.9 Dashboard mappings

### Onboarding Pipeline (6 items)
- [ ] 3.1 Enable multi-role selection during ingestion
- [ ] 3.2 Bulk upload dynamic validation
- [ ] 3.3 Bulk upload creates ApplicationPartnerType records
- [ ] 3.4 Conversion carries over all data
- [ ] 3.5 Add financial profiling step
- [ ] 3.6 Add master agent assignment

### RBAC Implementation (6 items)
- [ ] 4.1 Seed required permissions
- [ ] 4.2 Seed required user groups (roles)
- [ ] 4.3 Update login response to include permissions
- [ ] 4.4 Protect onboarding endpoints
- [ ] 4.5 Protect governance approval endpoints
- [ ] 4.6 Fix PermissionGroup integration

### Database Seeding (3 items)
- [ ] 5.1 Seed partner types
- [ ] 5.2 Seed choice lists
- [ ] 5.3 Seed system parameters

### Frontend Integration (5 items)
- [ ] 6.1 Create useChoices hook
- [ ] 6.2 Update AuthUser type
- [ ] 6.3 Update useAuth hook
- [ ] 6.4 Update sidebar with permission filtering
- [ ] 6.5 Create permission utility

### Testing & Validation (8 items)
- [ ] 7.1 Test dynamic partner types
- [ ] 7.2 Test role-conditional documents
- [ ] 7.3 Test approval workflow
- [ ] 7.4 Test RBAC enforcement
- [ ] 7.5 Test bulk upload
- [ ] 7.6 Test financial profiling
- [ ] 7.7 Test master agent assignment
- [ ] 7.8 Test data conversion

---

**Total Items:** 44  
**Completed:** 0  
**Remaining:** 44

---

## Notes & Issues

Use this section to track any issues encountered during implementation:

1. 
2. 
3. 

---

## Sign-Off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| System Administrator | | | |
| Compliance Officer | | | |
| Finance Manager | | | |
| ZIC Auditor | | | |

---

**Document Version:** 1.0  
**Last Updated:** 2026-06-26  
**Next Review:** Upon completion of all items