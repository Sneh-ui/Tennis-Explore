import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useFormik } from 'formik'
import { Icon } from '@/components/shared/icon'
import { SearchInput } from '@/components/shared/search-input'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Separator } from '@/components/ui/separator'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu'
import { useAuth } from '@/hooks/use-auth'
import { useUpdatePassword } from '@/hooks/use-users'
import { changePasswordSchema } from '@/lib/validations'

const getInitials = (name) =>
  name
    .split(' ')
    .filter(Boolean)
    .map((part) => part[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()

export function Header({ onMenuClick }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [pwdOpen, setPwdOpen] = useState(false)
  const updatePwdMutation = useUpdatePassword()

  const formikPwd = useFormik({
    initialValues: { current_password: '', new_password: '', confirm_password: '' },
    validationSchema: changePasswordSchema,
    onSubmit: async (values, { setStatus, setSubmitting, resetForm }) => {
      setStatus('')
      try {
        await updatePwdMutation.mutateAsync({
          current_password: values.current_password,
          new_password: values.new_password,
        })
        setStatus({ success: 'Password updated successfully' })
        setTimeout(() => {
          setPwdOpen(false)
          resetForm()
        }, 1200)
      } catch (err) {
        setStatus({ error: err.message })
      } finally {
        setSubmitting(false)
      }
    },
  })

  const handleSignOut = () => {
    logout()
    navigate('/', { replace: true })
  }

  return (
    <header className="flex justify-between items-center w-full px-8 h-[84px] bg-card border-b-2 border-primary/20 shrink-0 shadow-sm" style={{ height: '84px' }}>
      {/* Left side */}
      <div className="flex items-center gap-4 flex-1">
        <Button variant="ghost" size="icon" className="md:hidden" onClick={onMenuClick}>
          <Icon name="menu" className="text-foreground" />
        </Button>
        <div className="text-xl font-black tracking-tight text-primary uppercase">Tennis Explore</div>
        <SearchInput
          placeholder="Search matches, players, or clips..."
          className="max-w-md w-full ml-8 hidden lg:block"
        />
      </div>

      {/* Right side */}
      <div className="flex items-center gap-5">
        <Button variant="ghost" size="icon" className="relative">
          <Icon name="notifications" className="text-muted-foreground" />
          <span className="absolute top-2 right-2 w-2 h-2 bg-destructive rounded-full border-2 border-card" />
        </Button>
        <Button variant="ghost" size="icon">
          <Icon name="settings" className="text-muted-foreground" />
        </Button>
        <Separator orientation="vertical" className="h-10" />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              aria-label="Open profile menu"
              className="flex items-center gap-4 pl-4 pr-2 py-2 rounded-full bg-primary/10 border-2 border-primary/30 shadow-md hover:bg-primary/15 hover:border-primary/40 transition-all outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            >
              <div className="hidden sm:block text-right">
                <p className="text-[15px] font-extrabold text-foreground leading-none tracking-wide" style={{ fontSize: '15px' }}>{user?.name}</p>
                <p className="text-[13px] font-semibold text-primary uppercase tracking-wider" style={{ fontSize: '13px' }}>{user?.role}</p>
              </div>
              <Avatar className="h-12 w-12 border-[3px] border-primary shadow-lg">
                <AvatarFallback className="text-[16px] font-extrabold bg-primary text-primary-foreground">{getInitials(user?.name ?? 'TE')}</AvatarFallback>
              </Avatar>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-72 font-sans">
            <DropdownMenuLabel className="font-sans text-[14px] py-3">{user?.email}</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => setPwdOpen(true)} className="font-sans text-[14px] py-2.5">
              <Icon name="lock" className="text-muted-foreground mr-2" />
              Change Password
            </DropdownMenuItem>
            <DropdownMenuItem onClick={handleSignOut} className="font-sans text-[14px] py-2.5">
              <Icon name="logout" className="text-muted-foreground mr-2" />
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <Dialog open={pwdOpen} onOpenChange={(open) => { setPwdOpen(open); if (!open) formikPwd.resetForm(); }}>
        <DialogContent className="font-sans">
          <DialogHeader>
            <DialogTitle className="font-sans">Change Password</DialogTitle>
            <DialogDescription className="font-sans">Update your password. You will stay logged in.</DialogDescription>
          </DialogHeader>
          <form onSubmit={formikPwd.handleSubmit} className="space-y-4 mt-2 font-sans" noValidate>
            <div className="space-y-2">
              <Label htmlFor="current_password" className="font-sans">Current Password</Label>
              <Input
                id="current_password"
                name="current_password"
                type="password"
                value={formikPwd.values.current_password}
                onChange={formikPwd.handleChange}
                onBlur={formikPwd.handleBlur}
                className="font-sans"
                aria-invalid={!!(formikPwd.touched.current_password && formikPwd.errors.current_password)}
                aria-label="Current password"
              />
              {formikPwd.touched.current_password && formikPwd.errors.current_password && (
                <p className="text-sm text-destructive font-sans" role="alert">{formikPwd.errors.current_password}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="new_password" className="font-sans">New Password</Label>
              <Input
                id="new_password"
                name="new_password"
                type="password"
                value={formikPwd.values.new_password}
                onChange={formikPwd.handleChange}
                onBlur={formikPwd.handleBlur}
                className="font-sans"
                aria-invalid={!!(formikPwd.touched.new_password && formikPwd.errors.new_password)}
                aria-label="New password"
              />
              {formikPwd.touched.new_password && formikPwd.errors.new_password && (
                <p className="text-sm text-destructive font-sans" role="alert">{formikPwd.errors.new_password}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirm_password" className="font-sans">Confirm New Password</Label>
              <Input
                id="confirm_password"
                name="confirm_password"
                type="password"
                value={formikPwd.values.confirm_password}
                onChange={formikPwd.handleChange}
                onBlur={formikPwd.handleBlur}
                className="font-sans"
                aria-invalid={!!(formikPwd.touched.confirm_password && formikPwd.errors.confirm_password)}
                aria-label="Confirm new password"
              />
              {formikPwd.touched.confirm_password && formikPwd.errors.confirm_password && (
                <p className="text-sm text-destructive font-sans" role="alert">{formikPwd.errors.confirm_password}</p>
              )}
            </div>
            {formikPwd.status?.error && (
              <div className="flex items-center gap-2 rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2" role="alert" aria-live="polite">
                <Icon name="error" className="text-destructive text-sm" />
                <p className="text-sm text-destructive font-sans">{formikPwd.status.error}</p>
              </div>
            )}
            {formikPwd.status?.success && (
              <div className="flex items-center gap-2 rounded-lg border border-primary/40 bg-primary/10 px-3 py-2" role="status" aria-live="polite">
                <Icon name="check_circle" className="text-primary text-sm" />
                <p className="text-sm text-primary font-sans">{formikPwd.status.success}</p>
              </div>
            )}
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={()=>setPwdOpen(false)} className="font-sans">Cancel</Button>
              <Button type="submit" disabled={formikPwd.isSubmitting || updatePwdMutation.isPending} className="font-sans">
                {(formikPwd.isSubmitting || updatePwdMutation.isPending) && <Icon name="progress_activity" className="animate-spin text-sm" />}
                Update Password
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </header>
  )
}
