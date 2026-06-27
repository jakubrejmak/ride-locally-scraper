export default function PopOver({ className, children }: { className: string, children: React.ReactNode[] }) {
  return (
    <ul className={`panel z-20 relative ${className}`} >
      <li>{children}</li>
    </ul >
  )
}
