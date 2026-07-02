import type { Target } from "../../pages/add-target/page";

export default function TargetRow(target: Target): React.ReactNode {
  return (
    <div key={target.id} className="flex gap-3 justify-between">
      <span>
        {target.name}
      </span>
      <span className="flex gap-3 justify-between">
        <span>
          {target.is_active ? "Active" : "Inactive"}
        </span>
        <button>
          Run now
        </button>
      </span>
    </div>
  )
}
