import { createContext } from 'react'

const USERS_KEY = 'tennis-explore.users'

export const DEMO_ACCOUNT = {
  name: 'Alex Rivera',
  email: 'analyst@tennisexplore.au',
  password: 'ace123',
  role: 'Lead Analyst',
}

export const readJSON = (key) => {
  try {
    return JSON.parse(localStorage.getItem(key))
  } catch {
    return null
  }
}

const getRegisteredUsers = () => readJSON(USERS_KEY) ?? []

const findAccount = (email) => {
  const normalized = email.trim().toLowerCase()
  if (normalized === DEMO_ACCOUNT.email) return DEMO_ACCOUNT
  return getRegisteredUsers().find((account) => account.email.toLowerCase() === normalized)
}

export const authenticate = ({ email, password }) =>
  new Promise((resolve, reject) => {
    setTimeout(() => {
      const account = findAccount(email)
      if (!account || account.password !== password) {
        reject(new Error('Invalid email or password'))
        return
      }
      resolve(account)
    }, 600)
  })

export const registerAccount = ({ name, email, password }) =>
  new Promise((resolve, reject) => {
    setTimeout(() => {
      if (!name.trim()) {
        reject(new Error('Name is required'))
        return
      }
      if (findAccount(email)) {
        reject(new Error('An account with this email already exists'))
        return
      }
      const account = { name: name.trim(), email: email.trim().toLowerCase(), password, role: 'Analyst' }
      localStorage.setItem(USERS_KEY, JSON.stringify([...getRegisteredUsers(), account]))
      resolve(account)
    }, 600)
  })

export const AuthContext = createContext(null)
