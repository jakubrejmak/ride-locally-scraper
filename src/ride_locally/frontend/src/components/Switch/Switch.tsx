import { Switch as BaseSwitch } from "@base-ui/react/switch";

type Props = {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  id?: string;
  disabled?: boolean;
};

export default function Switch({ checked, onCheckedChange, id, disabled }: Props) {
  return (
    <BaseSwitch.Root
      id={id}
      checked={checked}
      onCheckedChange={onCheckedChange}
      disabled={disabled}
      className="relative inline-flex h-5 w-9 shrink-0 cursor-pointer items-center rounded-full border border-accent-light/20 bg-black/20 transition outline-none data-[checked]:border-accent-light/45 data-[checked]:bg-accent/40 focus-visible:shadow-[0_0_0_3px_rgb(249_115_22_/_0.2)] disabled:cursor-not-allowed disabled:opacity-50"
    >
      <BaseSwitch.Thumb className="block size-4 translate-x-0.5 rounded-full bg-white shadow transition-transform data-[checked]:translate-x-[18px]" />
    </BaseSwitch.Root>
  );
}
