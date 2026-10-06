import { useState } from 'react'
import { useFormik } from 'formik'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog'
import { Icon, PageHeader } from '@/components/shared'
import { TableSkeleton } from '@/components/ui/skeleton'
import { useAuth } from '@/hooks/use-auth'
import { useUsers, useCreateUser, useUpdateUser, useDeleteUser } from '@/hooks/use-users'
import { createUserSchema, updateUserSchema } from '@/lib/validations'

const ROLE_OPTIONS = ['admin', 'coach']

export default function AdminUsersPage() {
  const { user } = useAuth()
  const isAdmin = (user?.role || '').toLowerCase() === 'admin'

  const { data: users = [], isLoading, isError, error } = useUsers()
  const createMutation = useCreateUser()
  const updateMutation = useUpdateUser()
  const deleteMutation = useDeleteUser()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingUser, setEditingUser] = useState(null)
  const [deleteConfirm, setDeleteConfirm] = useState(null)

  const formik = useFormik({
    initialValues: { name: '', email: '', password: '', role: 'coach' },
    validationSchema: editingUser ? updateUserSchema : createUserSchema,
    enableReinitialize: true,
    onSubmit: async (values, { setSubmitting, setStatus }) => {
      setStatus('')
      try {
        if (editingUser) {
          const payload = { name: values.name.trim(), email: values.email.trim(), role: values.role }
          if (values.password) payload.password = values.password
          await updateMutation.mutateAsync({ id: editingUser.id, ...payload })
        } else {
          await createMutation.mutateAsync({
            name: values.name.trim(),
            email: values.email.trim(),
            password: values.password,
            role: values.role,
          })
        }
        setDialogOpen(false)
      } catch (err) {
        setStatus(err.message)
      } finally {
        setSubmitting(false)
      }
    },
  })

  if (!isAdmin) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-10rem)]">
        <Card className="p-8 text-center max-w-md font-sans">
          <Icon name="lock" className="text-4xl text-destructive mx-auto mb-4" />
          <h2 className="text-headline-md text-foreground font-sans">Access Denied</h2>
          <p className="text-muted-foreground mt-2 font-sans">Admin access required. Your role: {user?.role || 'Unknown'}</p>
        </Card>
      </div>
    )
  }

  const openCreate = () => {
    setEditingUser(null)
    formik.setValues({ name: '', email: '', password: '', role: 'coach' })
    formik.setStatus('')
    setDialogOpen(true)
  }

  const openEdit = (u) => {
    setEditingUser(u)
    formik.setValues({ name: u.name, email: u.email, password: '', role: u.role?.toLowerCase() || 'coach' })
    formik.setStatus('')
    setDialogOpen(true)
  }

  const handleDelete = async (u) => {
    try {
      await deleteMutation.mutateAsync(u.id)
      setDeleteConfirm(null)
    } catch (err) {
      // error handled via query error
    }
  }

  return (
    <div className="space-y-6 font-sans" style={{ fontFamily: "Inter, system-ui, sans-serif" }}>
      <PageHeader
        title="User Management"
        subtitle="Create, edit and remove platform users. Admin only."
        actions={
          <Button onClick={openCreate} className="font-sans">
            <Icon name="person_add" className="text-sm" /> Add User
          </Button>
        }
      />

      {isError && (
        <Card className="p-4 border-destructive/40 bg-destructive/10 flex items-center gap-2 font-sans">
          <Icon name="error" className="text-destructive" />
          <p className="text-sm text-destructive font-sans">{error?.message || 'Failed to load users'}</p>
          <Button variant="ghost" size="sm" className="ml-auto font-sans" onClick={() => window.location.reload()}>Retry</Button>
        </Card>
      )}

      <Card className="overflow-hidden">
        {isLoading ? (
          <div className="p-6">
            <TableSkeleton rows={5} cols={4} />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-te-outline-variant bg-te-surface-container-low">
                  <th className="px-6 py-4 text-[11px] font-bold uppercase tracking-wider text-muted-foreground font-sans">User</th>
                  <th className="px-6 py-4 text-[11px] font-bold uppercase tracking-wider text-muted-foreground font-sans">Email</th>
                  <th className="px-6 py-4 text-[11px] font-bold uppercase tracking-wider text-muted-foreground font-sans">Role</th>
                  <th className="px-6 py-4 text-[11px] font-bold uppercase tracking-wider text-muted-foreground text-right font-sans">Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="px-6 py-12 text-center text-muted-foreground font-sans">No users found</td>
                  </tr>
                ) : (
                  users.map((u) => (
                    <tr key={u.id} className="border-b border-te-outline-variant/30 hover:bg-te-surface-container-low">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-primary-container flex items-center justify-center text-xs font-bold text-primary-container-foreground font-sans">
                            {u.name.split(' ').map(s=>s[0]).slice(0,2).join('').toUpperCase()}
                          </div>
                          <span className="font-medium text-foreground font-sans">{u.name}</span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-sm text-muted-foreground font-sans">{u.email}</td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 text-[10px] font-bold rounded-full uppercase font-sans ${u.role?.toLowerCase()==='admin' ? 'bg-primary text-primary-foreground' : 'bg-te-surface-container-high text-foreground'}`}>
                          {u.role}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex justify-end gap-2">
                          <Button variant="ghost" size="sm" className="font-sans" onClick={() => openEdit(u)}>
                            <Icon name="edit" className="text-sm" /> Edit
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="text-destructive hover:text-destructive hover:bg-destructive/10 font-sans"
                            onClick={() => setDeleteConfirm(u)}
                            disabled={u.id === user?.id}
                            aria-label={`Delete user ${u.name}`}
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
        )}
      </Card>

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="font-sans">
          <DialogHeader>
            <DialogTitle className="font-sans">{editingUser ? 'Edit User' : 'Add User'}</DialogTitle>
            <DialogDescription className="font-sans">
              {editingUser ? 'Update user details. Leave password blank to keep current.' : 'Create a new platform user.'}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={formik.handleSubmit} className="space-y-4 mt-2 font-sans" noValidate>
            <div className="space-y-2">
              <Label htmlFor="name" className="font-sans">Name</Label>
              <Input
                id="name"
                name="name"
                value={formik.values.name}
                onChange={formik.handleChange}
                onBlur={formik.handleBlur}
                placeholder="Alex Rivera"
                className="font-sans"
                aria-invalid={!!(formik.touched.name && formik.errors.name)}
              />
              {formik.touched.name && formik.errors.name && (
                <p className="text-sm text-destructive font-sans" role="alert">{formik.errors.name}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="email" className="font-sans">Email</Label>
              <Input
                id="email"
                name="email"
                type="email"
                value={formik.values.email}
                onChange={formik.handleChange}
                onBlur={formik.handleBlur}
                placeholder="user@tennisexplore.au"
                className="font-sans"
                aria-invalid={!!(formik.touched.email && formik.errors.email)}
              />
              {formik.touched.email && formik.errors.email && (
                <p className="text-sm text-destructive font-sans" role="alert">{formik.errors.email}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="password" className="font-sans">{editingUser ? 'New Password (leave blank to keep)' : 'Password'}</Label>
              <Input
                id="password"
                name="password"
                type="password"
                value={formik.values.password}
                onChange={formik.handleChange}
                onBlur={formik.handleBlur}
                placeholder={editingUser ? '••••••••' : '••••••••'}
                className="font-sans"
                aria-invalid={!!(formik.touched.password && formik.errors.password)}
              />
              {formik.touched.password && formik.errors.password && (
                <p className="text-sm text-destructive font-sans" role="alert">{formik.errors.password}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label className="font-sans">Role</Label>
              <Select value={formik.values.role} onValueChange={(v)=>formik.setFieldValue('role', v)}>
                <SelectTrigger className="font-sans" aria-label="Role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ROLE_OPTIONS.map(r=>(
                    <SelectItem key={r} value={r} className="font-sans">{r.charAt(0).toUpperCase()+r.slice(1)}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {formik.touched.role && formik.errors.role && (
                <p className="text-sm text-destructive font-sans" role="alert">{formik.errors.role}</p>
              )}
            </div>
            {formik.status && (
              <div className="flex items-center gap-2 rounded-lg border border-destructive/40 bg-destructive/10 px-3 py-2" role="alert" aria-live="polite">
                <Icon name="error" className="text-destructive text-sm" />
                <p className="text-sm text-destructive font-sans">{formik.status}</p>
              </div>
            )}
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={()=>setDialogOpen(false)} className="font-sans">Cancel</Button>
              <Button type="submit" disabled={formik.isSubmitting || createMutation.isPending || updateMutation.isPending} className="font-sans">
                {(formik.isSubmitting || createMutation.isPending || updateMutation.isPending) && <Icon name="progress_activity" className="animate-spin text-sm" />}
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
