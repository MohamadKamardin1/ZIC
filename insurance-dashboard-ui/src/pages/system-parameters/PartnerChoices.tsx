import { PageHeader } from "./SharedComponents"
import ChoiceListManager from "./ChoiceListManager"

export default function PartnerChoices() {
  return (
    <div>
      <PageHeader
        title="Dropdown Choices"
        description="All selectable options used throughout partner onboarding. Add, edit, or remove options from each choice list."
      />
      <ChoiceListManager
        title="Choice Lists"
        description="Each list represents a dropdown in the application forms. You can add/rename/delete both lists and their individual options."
      />
    </div>
  )
}
