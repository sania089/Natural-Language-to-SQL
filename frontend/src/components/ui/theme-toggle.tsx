import { Moon, Sun } from 'lucide-react'
import { useTheme } from '@/hooks/useTheme'
import { IconButton } from './button'
import { Tooltip } from './tooltip'

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme()
  const next = theme === 'dark' ? 'light' : 'dark'
  const Icon = theme === 'dark' ? Sun : Moon
  return (
    <Tooltip content={`Switch to ${next} theme`}>
      <IconButton label={`Switch to ${next} theme`} onClick={toggleTheme}>
        <Icon className="h-5 w-5" aria-hidden="true" />
      </IconButton>
    </Tooltip>
  )
}
