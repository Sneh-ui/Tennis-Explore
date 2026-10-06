import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useFormik } from 'formik'
import { Icon } from '@/components/shared/icon'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { DEMO_ACCOUNT } from '@/context/auth-context'
import { useAuth } from '@/hooks/use-auth'
import { hasPendingQuery } from '@/lib/pending-query'
import { loginSchema } from '@/lib/validations'

const GLASS_STYLE = {
  background: 'rgba(18, 20, 28, 0.6)',
  backdropFilter: 'blur(20px)',
  border: '1px solid rgba(255, 255, 255, 0.05)',
}

const INPUT_CLASSES = 'h-11 border-white/10 bg-white/[0.04] text-foreground placeholder:text-muted-foreground/60 focus-visible:bg-white/[0.06] transition-colors'

function Wordmark() {
  return (
    <div className="flex flex-col items-center gap-3">
      <p className="text-label-md uppercase tracking-[0.3em] text-primary" style={{ fontFamily: "Inter, system-ui, sans-serif" }}>Performance Intelligence Platform</p>
      <Link to="/" className="flex items-baseline gap-1 tracking-tight" style={{ fontFamily: "Inter, system-ui, sans-serif", fontSize: 40 }}>
        <span className="font-extrabold italic text-white">Tennis</span>
        <span className="font-light text-primary">Explore</span>
      </Link>
    </div>
  )
}

export default function LoginPage() {
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [showPassword, setShowPassword] = useState(false)
  const [serverError, setServerError] = useState('')
  const redirectTo = location.state?.from?.pathname ?? '/ai-chatbot'

  const formik = useFormik({
    initialValues: { email: '', password: '' },
    validationSchema: loginSchema,
    onSubmit: async (values, { setSubmitting }) => {
      setServerError('')
      try {
        await login({ email: values.email, password: values.password })
        navigate(hasPendingQuery() ? '/ai-chatbot' : redirectTo, { replace: true })
      } catch (err) {
        setServerError(err.message)
      } finally {
        setSubmitting(false)
      }
    },
  })

  if (user) {
    return <Navigate to="/ai-chatbot" replace />
  }

  const fillDemoCredentials = () => {
    formik.setValues({ email: DEMO_ACCOUNT.email, password: DEMO_ACCOUNT.password })
    setServerError('')
  }
  const fillCoachCredentials = () => {
    formik.setValues({ email: 'coach@tennisexplore.au', password: 'coach123' })
    setServerError('')
  }

  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-[#02030A] font-sans" style={{ fontFamily: "Inter, system-ui, sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap" rel="stylesheet" />

      {/* Ambient glow orbs */}
      <motion.div
        animate={{ y: [0, -30, 0], opacity: [0.12, 0.2, 0.12] }}
        transition={{ duration: 9, repeat: Infinity, ease: 'easeInOut' }}
        className="absolute top-[12%] left-[8%] h-[460px] w-[460px] rounded-full"
        style={{ background: 'radial-gradient(circle, rgba(99,102,241,0.14) 0%, transparent 70%)' }}
      />
      <motion.div
        animate={{ y: [0, 24, 0], opacity: [0.08, 0.16, 0.08] }}
        transition={{ duration: 11, repeat: Infinity, ease: 'easeInOut', delay: 2 }}
        className="absolute bottom-[8%] right-[6%] h-[400px] w-[400px] rounded-full"
        style={{ background: 'radial-gradient(circle, rgba(194,233,78,0.09) 0%, transparent 70%)' }}
      />

      <main className="relative z-10 flex min-h-screen flex-col items-center justify-center gap-10 px-6 py-12">
        <Wordmark />

        <motion.div
          initial={{ opacity: 0, y: 32 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          className="w-full max-w-md rounded-2xl p-8 shadow-2xl"
          style={GLASS_STYLE}
        >
          <div className="mb-6">
            <h1 className="text-headline-lg text-foreground font-sans">Welcome back</h1>
            <p className="mt-1 text-body-md text-muted-foreground font-sans">
              Sign in to access your analytics workspace.
            </p>
          </div>

          <form onSubmit={formik.handleSubmit} className="space-y-5" noValidate>
            <div className="space-y-2">
              <Label htmlFor="email" className="font-sans">Email</Label>
              <Input
                id="email"
                name="email"
                type="email"
                placeholder="you@tennisexplore.au"
                value={formik.values.email}
                onChange={formik.handleChange}
                onBlur={formik.handleBlur}
                autoComplete="email"
                className={`${INPUT_CLASSES} font-sans`}
                aria-invalid={!!(formik.touched.email && formik.errors.email)}
                aria-describedby={formik.errors.email ? 'email-error' : undefined}
              />
              {formik.touched.email && formik.errors.email && (
                <p id="email-error" className="text-sm text-destructive font-sans" role="alert">{formik.errors.email}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className="font-sans">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••"
                  value={formik.values.password}
                  onChange={formik.handleChange}
                  onBlur={formik.handleBlur}
                  autoComplete="current-password"
                  className={`${INPUT_CLASSES} pr-11 font-sans`}
                  aria-invalid={!!(formik.touched.password && formik.errors.password)}
                  aria-describedby={formik.errors.password ? 'password-error' : undefined}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
                >
                  <Icon name={showPassword ? 'visibility_off' : 'visibility'} />
                </button>
              </div>
              {formik.touched.password && formik.errors.password && (
                <p id="password-error" className="text-sm text-destructive font-sans" role="alert">{formik.errors.password}</p>
              )}
            </div>

            {serverError && (
              <div className="flex items-center gap-2 rounded-xl border border-destructive/40 bg-destructive/10 px-3 py-2.5" role="alert" aria-live="polite">
                <Icon name="error" className="text-xl text-destructive" />
                <p className="text-body-md text-destructive font-sans">{serverError}</p>
              </div>
            )}

            <Button type="submit" size="lg" disabled={formik.isSubmitting} className="w-full font-sans shadow-[0_0_24px_rgba(194,233,78,0.25)] hover:shadow-[0_0_36px_rgba(194,233,78,0.35)]">
              {formik.isSubmitting ? (
                <>
                  <Icon name="progress_activity" className="animate-spin text-base" />
                  Signing in...
                </>
              ) : (
                <>
                  <Icon name="login" className="text-base" />
                  Sign In
                </>
              )}
            </Button>
          </form>

          <div className="mt-6 rounded-xl border border-dashed border-te-outline bg-white/[0.02] p-4 space-y-3">
            <p className="text-label-md uppercase tracking-wider text-muted-foreground font-sans" style={{ fontFamily: "Inter, system-ui, sans-serif" }}>Demo Access</p>
            <div className="flex items-center justify-between">
              <p className="text-body-md text-muted-foreground font-sans" style={{ fontFamily: "Inter, system-ui, sans-serif" }}>
                {DEMO_ACCOUNT.email} / {DEMO_ACCOUNT.password} <span className="text-xs uppercase tracking-wider ml-1">admin</span>
              </p>
              <Button type="button" variant="link" size="sm" className="h-auto p-0 font-sans" onClick={fillDemoCredentials}>
                Fill admin
              </Button>
            </div>
            <div className="flex items-center justify-between">
              <p className="text-body-md text-muted-foreground font-sans" style={{ fontFamily: "Inter, system-ui, sans-serif" }}>
                coach@tennisexplore.au / coach123 <span className="text-xs uppercase tracking-wider ml-1">coach</span>
              </p>
              <Button type="button" variant="link" size="sm" className="h-auto p-0 font-sans" onClick={fillCoachCredentials}>
                Fill coach
              </Button>
            </div>
          </div>

          {/* Signup disabled for now — login-only feature
          <p className="mt-6 text-center text-body-md text-muted-foreground">
            {isSignup ? 'Already have an account?' : "Don't have an account?"}
            <button type="button" onClick={switchMode} className="ml-1.5 font-semibold text-primary hover:underline">
              {isSignup ? 'Sign in' : 'Create one'}
            </button>
          </p>
          */}
        </motion.div>

        <Link to="/" className="flex items-center gap-2 text-label-md uppercase tracking-wider text-muted-foreground transition-colors hover:text-primary">
          <Icon name="arrow_back" className="text-base" />
          Back to explore
        </Link>
      </main>
    </div>
  )
}
