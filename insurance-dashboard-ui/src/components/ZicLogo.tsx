export function ZicLogo({ size = 40 }: { size?: number }) {
  return (
    <div className="inline-flex items-center justify-center leading-none">
      <img
        src="/upscaled_zic_logo.png"
        alt="ZIC Logo"
        style={{ height: size, width: "auto" }}
        className="object-contain"
      />
    </div>
  )
}
