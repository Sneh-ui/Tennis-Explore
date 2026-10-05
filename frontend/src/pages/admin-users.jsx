import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Icon, PageHeader } from '@/components/shared'
import { useAuth } from '@/hooks/use-auth'
import { listUsers, createUser, updateUser, deleteUser } from '@/lib/api'

const ROLE_OPTIONS = ['Analyst', 'Lead Analyst', 'Admin']

export default function AdminUsersPage() {
  const { user, token } = useAuth()
  const isAdmin = (user?.role || '').toLowerCase() === 'admin'

  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  const [form, setForm] = useState({ name: '', email: '', password: '', role: 'Analyst' })
  const [formError, setFormError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const [deleteConfirm, setDeleteConfirm] = useState(null)

  const loadUsers = async () => {
    if (!token) return
    setLoading(true)
    setError('')
    try {
      const data = await listUsers(token)
      setUsers(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isAdmin) loadUsers()
    else setLoading(false)
  }, [isAdmin, token])

  if (!isAdmin) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-10rem)]">
        <Card className="p-8 text-center max-w-md">
          <Icon name="lock" className="text-4xl text-destructive mx-auto mb-4" />
          <h2 className="text-headline-md text-foreground">Access Denied</h2>
          <p className="text-muted-foreground mt-2">Admin access required. Your role: {user?.role || 'Unknown'}</p>
        </Card>
      </div>
    )
  }

  const openCreate = () => {
    setEditingUser(null)
    setForm({ name: '', email: '', password: '', role: 'Analyst' })
    setFormError('')
    setDialogOpen(true)
  }

  const openEdit = (u) => {
    setEditingUser(u)
    setForm({ name: u.name, email: u.email, password: '', role: u.role })
    setFormError('')
    setDialogOpen(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setFormError('')
    if (!form.name.trim()) return setFormError('Name is required')
    if (!form.email.trim()) return setFormError('Email is required')
    if (!editingUser && !form.password) return setFormError('Password is required')
    if (form.password && form.password.length < 6) return setFormError('Password must be at least 6 characters')

    setSubmitting(true)
    try {
      if (editingUser) {
        const payload = { name: form.name.trim(), email: form.email.trim(), role: form.role }
        if (form.password) payload.password = form.password
        await updateUser(token, editingUser.id, payload)
      } else {
        await createUser(token, {
          name: form.name.trim(),
          email: form.email.trim(),
          password: form.password,
          role: form.role,
        })
      }
      setDialogOpen(false)
      await loadUsers()
    } catch (err) {
      setFormError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleDelete = async (u) => {
    try {
      await deleteUser(token, u.id)
      setDeleteConfirm(null)
      await loadUsers()
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="User Management"
        subtitle="Create, edit and remove platform users. Admin only."
        actions={
          <Button onClick={openCreate}>
            <Icon name="person_add" className="text-sm" /> Add User
          </Button>
        }
      />

      {error && (
        <Card className="p-4 border-destructive/40 bg-destructive/10 flex items-center gap-2">
          <Icon name="error" className="text-destructive" />
          <p className="text-sm text-destructive">{error}</p>
          <Button variant="ghost" size="sm" className="ml-auto" onClick={loadUsers}>Retry</Button>
        </Card>
      )}

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-te-outline-variant bg-te-surface-container-low">
                <th className="px-6 py-4 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">User</th>
                <th className="px-6 py-4 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Email</th>
                <th className="px-6 py-4 text-[11px] font-bold uppercase tracking-wider text-muted-foreground">Role</th>
                <th className="px-6 py-4 text-[11px] font-bold uppercase tracking-wider text-muted-foreground text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={4} className="px-6 py-12 text-center">
                    <Icon name="progress_activity" className="animate-spin text-2xl text-primary mx-auto" />
                    <p className="text-sm text-muted-foreground mt-2">Loading users...</p>
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-12 text-center text-muted-foreground">No users found</td>
                </tr>
              ) : (
                users.map((u) => (
                  <tr key={u.id} className="border-b border-te-outline-variant/30 hover:bg-te-surface-container-low">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-primary-container flex items-center justify-center text-xs font-bold text-primary-container-foreground">
                          {u.name.split(' ').map(s=>s[0]).slice(0,2).join('').toUpperCase()}
                        </div>
                        <span className="font-medium text-foreground">{u.name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-sm text-muted-foreground">{u.email}</td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 text-[10px] font-bold rounded-full uppercase ${u.role?.toLowerCase()==='admin' ? 'bg-primary text-primary-foreground' : 'bg-te-surface-container-high text-foreground'}`}>
                        {u.role}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex justify-end gap-2">
                        <Button variant="ghost" size="sm" onClick={() => openEdit(u)}>
                          <Icon name="edit" className="text-sm" /> Edit
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:text-destructive hover:bg-destructive/10"
                          onClick={() => setDeleteConfirm(u)}
                          disabled={u.id === user?.id}
                        >
                          <Icon name="delete" className="text-sm" /> Delete
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingUser ? 'Edit User' : 'Add User'}</DialogTitle>
            <DialogDescription>
              {editingUser ? 'Update user details. Leave password blank to keep current.' : 'Create a new platform user.'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4 mt-2">
            <div className="space-y-2">
              <Label htmlFor="name">Name</Label>
              <Input id="name" value={form.name} onChange={(e)=>setForm(p=>({...p, name:e.target.value}))} placeholder="Alex Rivera" required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" value={form.email} onChange={(e)=>setForm(p=>({...p, email:e.target.value}))} placeholder="user@tennisexplore.au" required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">{editingUser ? 'New Password (leave blank to keep)' : 'Password'}</Label>
              <Input id="password" type="password" value={form.password} onChange={(e)=>setForm(p=>({...p, password:e.target.value}))} placeholder={editingUser ? '••••••••' : '••••••••'} required={!editingUser} />
            </div>
            <div className="space-y-2">
              <Label>Role</Label>
              <Select value={form.role} onValueChange={(v)=>setForm(p=>({...p, role:v}))}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ROLE_OPTIONS.map(r=>(
                    <SelectItem key={r} value={r}>{r}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {formError && (
              <div className="flex items-center gap-2 rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2">
                <Icon name="error" className="text-destructive text-sm" />
                <p className="text-sm text-destructive">{formError}</p>
              </div>
            )}
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={()=>setDialogOpen(false)}>Cancel</Button>
              <Button type="submit" disabled={submitting}>
                {submitting && <Icon name="progress_activity" className="animate-spin text-sm" />}
                {editingUser ? 'Save Changes' : 'Create User'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirm Dialog */}
      <Dialog open={Boolean(deleteConfirm)} onOpenChange={(open)=>!open && setDeleteConfirm(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Delete User</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete <span className="font-semibold text-foreground">{deleteConfirm?.name}</span> ({deleteConfirm?.email})? This cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2 mt-4">
            <Button variant="outline" onClick={()=>setDeleteConfirm(null)}>Cancel</Button>
            <Button variant="destructive" onClick={()=>handleDelete(deleteConfirm)}>Delete</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
