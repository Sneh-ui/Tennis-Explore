import * as Yup from 'yup'

export const loginSchema = Yup.object({
  email: Yup.string().email('Invalid email').required('Email is required'),
  password: Yup.string().min(6, 'Password must be at least 6 characters').required('Password is required'),
})

export const createUserSchema = Yup.object({
  name: Yup.string().trim().required('Name is required').max(150, 'Name too long'),
  email: Yup.string().email('Invalid email').required('Email is required'),
  password: Yup.string().min(6, 'Must be at least 6 characters').required('Password is required'),
  role: Yup.string().oneOf(['admin', 'coach'], 'Role must be admin or coach').required('Role is required'),
})

export const updateUserSchema = Yup.object({
  name: Yup.string().trim().required('Name is required').max(150, 'Name too long'),
  email: Yup.string().email('Invalid email').required('Email is required'),
  password: Yup.string().min(6, 'Must be at least 6 characters').nullable().notRequired(),
  role: Yup.string().oneOf(['admin', 'coach'], 'Role must be admin or coach').required('Role is required'),
})

export const changePasswordSchema = Yup.object({
  current_password: Yup.string().required('Current password is required'),
  new_password: Yup.string().min(6, 'Must be at least 6 characters').required('New password is required'),
  confirm_password: Yup.string()
    .oneOf([Yup.ref('new_password')], 'Passwords must match')
    .required('Confirm password is required'),
})
