from apps.users.models import User

u = User.objects.get(username='testapp')
print('Before - is_approved:', getattr(u, 'is_approved', 'N/A'), 'is_active:', u.is_active)

u.is_active = True
if hasattr(u, 'is_approved'):
    u.is_approved = True
    u.save(update_fields=['is_active', 'is_approved'])
else:
    u.save(update_fields=['is_active'])

print('After - is_approved:', getattr(u, 'is_approved', 'N/A'), 'is_active:', u.is_active)
print('User approved successfully')
