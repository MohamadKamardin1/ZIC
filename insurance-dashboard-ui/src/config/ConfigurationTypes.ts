export interface ChoiceOption {
  value: string;
  label: string;
}

export interface ChoicesResponse {
  partnerTypes: ChoiceOption[];
  identificationTypes: ChoiceOption[];
  titles: ChoiceOption[];
  genders: ChoiceOption[];
  maritalStatuses: ChoiceOption[];
  politicalRisks: ChoiceOption[];
  amlRisks: ChoiceOption[];
  industries: ChoiceOption[];
  nationalities: ChoiceOption[];
  applicationStatuses: ChoiceOption[];
  documentTypes: ChoiceOption[];
  taskTypes: ChoiceOption[];
  taskStatuses: ChoiceOption[];
  taskPriorities: ChoiceOption[];
}

export interface WorkflowConfig {
  state_machine: Record<string, string[]>;
  terminal_statuses: string[];
  all_statuses: string[];
  status_labels: Record<string, string>;
}

export interface ContactTypeLabel {
  value: string;
  label: string;
}
