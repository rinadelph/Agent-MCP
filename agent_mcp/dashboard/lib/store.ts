import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface ThemeState {
  theme: 'light' | 'dark' | 'system'
  setTheme: (theme: 'light' | 'dark' | 'system') => void
  isDark: boolean
  toggleTheme: () => void
}

export const useTheme = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: 'system',
      isDark: false,
      setTheme: (theme) => {
        set({ theme })
        
        // Only run in browser environment
        if (typeof window !== 'undefined') {
          const isDark = theme === 'dark' || 
            (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)
          set({ isDark })
          
          // Update document class
          if (isDark) {
            document.documentElement.classList.add('dark')
          } else {
            document.documentElement.classList.remove('dark')
          }
        }
      },
      toggleTheme: () => {
        const currentTheme = get().theme
        const newTheme = currentTheme === 'light' ? 'dark' : 'light'
        get().setTheme(newTheme)
      }
    }),
    {
      name: 'theme-storage',
    }
  )
)

interface SidebarState {
  isCollapsed: boolean
  setCollapsed: (collapsed: boolean) => void
  toggle: () => void
}

export const useSidebar = create<SidebarState>()((set, get) => ({
  isCollapsed: false,
  setCollapsed: (collapsed) => set({ isCollapsed: collapsed }),
  toggle: () => set({ isCollapsed: !get().isCollapsed })
}))

interface DashboardState {
  currentView: 'overview' | 'agents' | 'tasks' | 'system'
  setCurrentView: (view: 'overview' | 'agents' | 'tasks' | 'system') => void
  isLoading: boolean
  setLoading: (loading: boolean) => void
  lastUpdated: Date | null
  setLastUpdated: (date: Date) => void
}

export const useDashboard = create<DashboardState>()((set) => ({
  currentView: 'overview',
  setCurrentView: (view) => set({ currentView: view }),
  isLoading: false,
  setLoading: (loading) => set({ isLoading: loading }),
  lastUpdated: null,
  setLastUpdated: (date) => set({ lastUpdated: date })
}))

interface CommandPaletteState {
  isOpen: boolean
  setOpen: (open: boolean) => void
  toggle: () => void
}

export const useCommandPalette = create<CommandPaletteState>()((set, get) => ({
  isOpen: false,
  setOpen: (open) => set({ isOpen: open }),
  toggle: () => set({ isOpen: !get().isOpen })
}))

interface NotificationState {
  notifications: Array<{
    id: string
    title: string
    message: string
    type: 'info' | 'success' | 'warning' | 'error'
    timestamp: Date
    read: boolean
  }>
  addNotification: (notification: Omit<NotificationState['notifications'][0], 'id' | 'timestamp' | 'read'>) => void
  markAsRead: (id: string) => void
  removeNotification: (id: string) => void
  clearAll: () => void
}

export const useNotifications = create<NotificationState>()((set, get) => ({
  notifications: [],
  addNotification: (notification) => {
    const newNotification = {
      ...notification,
      id: Math.random().toString(36).substr(2, 9),
      timestamp: new Date(),
      read: false
    }
    set({ 
      notifications: [newNotification, ...get().notifications].slice(0, 50) // Keep only latest 50
    })
  },
  markAsRead: (id) => {
    set({
      notifications: get().notifications.map(n => 
        n.id === id ? { ...n, read: true } : n
      )
    })
  },
  removeNotification: (id) => {
    set({
      notifications: get().notifications.filter(n => n.id !== id)
    })
  },
  clearAll: () => set({ notifications: [] })
}))

interface SearchState {
  query: string
  setQuery: (query: string) => void
  results: unknown[]
  setResults: (results: unknown[]) => void
  isSearching: boolean
  setSearching: (searching: boolean) => void
}

export const useSearch = create<SearchState>()((set) => ({
  query: '',
  setQuery: (query) => set({ query }),
  results: [],
  setResults: (results) => set({ results }),
  isSearching: false,
  setSearching: (searching) => set({ isSearching: searching })
}))