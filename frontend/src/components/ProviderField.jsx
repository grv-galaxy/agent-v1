export default function ProviderField({
  id,
  label,
  children,
  hint,
  error,
}) {
  return (
    <div className="space-y-2">
      <label htmlFor={id} className="block text-[13px] font-medium text-[#94A3B8]">
        {label}
      </label>
      {children}
      {hint ? <p className="text-xs leading-5 text-[#64748B]">{hint}</p> : null}
      {error ? (
        <p className="text-sm leading-5 text-red-300" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
