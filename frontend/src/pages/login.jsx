import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Icon } from '@/components/shared/icon'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { DEMO_ACCOUNT } from '@/context/auth-context'
import { useAuth } from '@/hooks/use-auth'
import { hasPendingQuery } from '@/lib/pending-query'

const GLASS_STYLE = {
  background: 'rgba(18, 20, 28, 0.6)',
  backdropFilter: 'blur(20px)',
  border: '1px solid rgba(255, 255, 255, 0.05)',
}

const INPUT_CLASSES = 'h-11 border-white/10 bg-white/[0.04] text-foreground placeholder:text-muted-foreground/60 focus-visible:bg-white/[0.06] transition-colors'

function Wordmark() {
  return (
    <div className="flex flex-col items-center gap-3">
      <p className="text-label-md uppercase tracking-[0.3em] text-primary">Performance Intelligence Platform</p>
      <Link to="/" className="flex items-baseline gap-1 tracking-tight" style={{ fontFamily: "'Playfair Display', serif", fontSize: 40 }}>
        <span className="font-extrabold italic text-white">Tennis</span>
        <span className="font-light text-primary">Explore</span>
      </Link>
    </div>
  )
}

export default function LoginPage() {
  const { user, login, signup } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  // Signup disabled for now — login-only feature
  // const [mode, setMode] = useState('login')
  const [mode] = useState('login')
  const [form, setForm] = useState({ name: '', email: '', password: '' })
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (user) {
    return <Navigate to="/ai-chatbot" replace />
    // return <Navigate to="/dashboard" replace /> 
  }

  const isSignup = mode === 'signup'
  const redirectTo = location.state?.from?.pathname ?? '/ai-chatbot'
  // const redirectTo = location.state?.from?.pathname ?? '/dashboard' 

  const setField = (field) => (event) => {
    setForm((prev) => ({ ...prev, [field]: event.target.value }))
    setError('')
  }

  const fillDemoCredentials = () => {
    setForm({ name: '', email: DEMO_ACCOUNT.email, password: DEMO_ACCOUNT.password })
    setError('')
  }

  // Signup disabled for now — login-only feature
  // const switchMode = () => {
  //   setMode(isSignup ? 'login' : 'signup')
  //   setError('')
  // }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await (isSignup
        ? signup({ name: form.name, email: form.email, password: form.password })
        : login({ email: form.email, password: form.password })
      )
      navigate(hasPendingQuery() ? '/ai-chatbot' : redirectTo, { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="relative min-h-screen w-full overflow-hidden bg-[#02030A] font-sans">
      <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400..900;1,400..900&display=swap" rel="stylesheet" />

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
            <h1 className="text-headline-lg text-foreground">{isSignup ? 'Create your account' : 'Welcome back'}</h1>
            <p className="mt-1 text-body-md text-muted-foreground">
              {isSignup ? 'Join the Tennis Explore analytics platform.' : 'Sign in to access your analytics workspace.'}
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-5" noValidate>
            {isSignup && (
              <div className="space-y-2">
                <Label htmlFor="name">Full Name</Label>
                <Input id="name" type="text" placeholder="Alex Rivera" value={form.name} onChange={setField('name')} autoComplete="name" required className={INPUT_CLASSES} />
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" placeholder="you@tennisexplore.au" value={form.email} onChange={setField('email')} autoComplete="email" required className={INPUT_CLASSES} />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input id="password" type={showPassword ? 'text' : 'password'} placeholder="••••••••" value={form.password} onChange={setField('password')} autoComplete={isSignup ? 'new-password' : 'current-password'} required className={`${INPUT_CLASSES} pr-11`} />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground transition-colors hover:text-foreground"
                >
                  <Icon name={showPassword ? 'visibility_off' : 'visibility'} />
                </button>
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 rounded-xl border border-destructive/40 bg-destructive/10 px-3 py-2.5">
                <Icon name="error" className="text-xl text-destructive" />
                <p className="text-body-md text-destructive">{error}</p>
              </div>
            )}

            <Button type="submit" size="lg" disabled={submitting} className="w-full shadow-[0_0_24px_rgba(194,233,78,0.25)] hover:shadow-[0_0_36px_rgba(194,233,78,0.35)]">
              {submitting ? (
                <>
                  <Icon name="progress_activity" className="animate-spin text-base" />
                  {isSignup ? 'Creating account...' : 'Signing in...'}
                </>
              ) : (
                <>
                  <Icon name="login" className="text-base" />
                  {isSignup ? 'Create Account' : 'Sign In'}
                </>
              )}
            </Button>
          </form>

          {!isSignup && (
            <div className="mt-6 rounded-xl border border-dashed border-te-outline bg-white/[0.02] p-4">
              <p className="text-label-md uppercase tracking-wider text-muted-foreground">Demo Access</p>
              <p className="mt-2 text-body-md text-muted-foreground">
                {DEMO_ACCOUNT.email} / {DEMO_ACCOUNT.password}
              </p>
              <Button type="button" variant="link" size="sm" className="mt-1 h-auto p-0" onClick={fillDemoCredentials}>
                Fill demo credentials
              </Button>
            </div>
          )}

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
