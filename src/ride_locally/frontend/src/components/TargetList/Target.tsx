import type { Target } from "../../pages/add-target/page";

export default function TargetRow(target: Target): React.ReactNode {
  return (
    <div key={target.id} className="flex">
      {target.name}
    </div>
  )
}
