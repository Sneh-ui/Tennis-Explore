import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select'
import { cn } from '@/lib/utils'

export function FormField({ label, name, error, children, className, ...props }) {
  return (
    <div className={cn('space-y-2', className)}>
      {label && <Label htmlFor={name} className="font-sans">{label}</Label>}
      {children}
      {error && <p className="text-sm text-destructive font-sans" role="alert">{error}</p>}
    </div>
  )
}

export function FormInput({ label, name, error, ...props }) {
  return (
    <FormField label={label} name={name} error={error}>
      <Input id={name} name={name} {...props} className={cn('font-sans', props.className)} aria-invalid={!!error} aria-describedby={error ? `${name}-error` : undefined} />
    </FormField>
  )
}

export function FormSelect({ label, name, value, onValueChange, options, error, placeholder = 'Select...' }) {
  return (
    <FormField label={label} name={name} error={error}>
      <Select value={value} onValueChange={onValueChange}>
        <SelectTrigger id={name} className="font-sans" aria-label={label}>
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          {options.map((opt) => {
            const val = typeof opt === 'string' ? opt : opt.value
            const lab = typeof opt === 'string' ? opt.charAt(0).toUpperCase() + opt.slice(1) : opt.label
            return <SelectItem key={val} value={val} className="font-sans">{lab}</SelectItem>
          })}
        </SelectContent>
      </Select>
    </FormField>
  )
}
