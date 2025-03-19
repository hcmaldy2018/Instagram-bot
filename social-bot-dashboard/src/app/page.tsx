"use client"

import { Button } from "@/components/ui/button"
import { useState, useEffect } from "react"
import { Eye, EyeOff } from 'lucide-react'
import { BrowserPreview } from "@/components/BrowserPreview"

export default function Home() {
  const [isLoading, setIsLoading] = useState(false)
  const [platform, setPlatform] = useState("instagram")
  const [username, setUsername] = useState("")
  const [storedUsernames, setStoredUsernames] = useState<string[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [password, setPassword] = useState("")
  const [showPassword, setShowPassword] = useState(true)
  const [interactions, setInteractions] = useState("1")
  const [output, setOutput] = useState<string[]>([])
  const [controller, setController] = useState<AbortController | null>(null)
  const [isLocalAccount, setIsLocalAccount] = useState(false)

  // Load stored usernames from localStorage on component mount
  useEffect(() => {
    const savedUsernames = localStorage.getItem('storedUsernames')
    if (savedUsernames) {
      setStoredUsernames(JSON.parse(savedUsernames))
    }
  }, [])

  // Save username to localStorage after successful bot launch
  const saveUsername = (username: string) => {
    const updatedUsernames = Array.from(new Set([...storedUsernames, username]))
    setStoredUsernames(updatedUsernames)
    localStorage.setItem('storedUsernames', JSON.stringify(updatedUsernames))
  }

  const handleLaunchBot = async () => {
    setIsLoading(true)
    setOutput([])
    saveUsername(username) // Save username when bot is launched

    // Create a new AbortController for this session
    const abortController = new AbortController()
    setController(abortController)

    try {
      const response = await fetch('/api/bot', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          platform,
          username,
          password,
          interactions: parseInt(interactions),
          isLocalAccount
        }),
        signal: abortController.signal
      })

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No reader available')

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const text = new TextDecoder().decode(value)
        const lines = text.split('\n').filter(line => line.trim())
        setOutput(prev => [...prev, ...lines])
      }
    } catch (error: any) {
      if (error.name === 'AbortError') {
        setOutput(prev => [...prev, 'Bot process terminated by user'])
      } else {
        setOutput(prev => [...prev, `Error: ${error}`])
      }
    } finally {
      setIsLoading(false)
      setController(null)
    }
  }

  const handleStopBot = () => {
    if (controller) {
      controller.abort()
      setOutput(prev => [...prev, 'Stopping bot...'])
    }
  }

  const handleClearFields = () => {
    setUsername("")
    setPassword("")
    setInteractions("1")
    setOutput([])
    const interactionsInput = document.querySelector('input[type="number"]') as HTMLInputElement
    if (interactionsInput) {
      interactionsInput.value = "1"
    }
  }

  return (
    <div className="flex min-h-screen">
      <div className="w-[600px]">
        <div className="p-8">
          <h2 className="text-lg mb-4">Bot Configuration</h2>
          <div className="space-y-4">
            <select
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
              className="w-full p-2 border rounded bg-white"
            >
              <option value="instagram">Instagram</option>
              <option value="facebook" disabled>Facebook (Coming Soon)</option>
            </select>
            <div className="relative">
              <input
                type="text"
                placeholder={`${platform === 'instagram' ? 'Instagram' : 'Facebook'} Username`}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                onFocus={() => setShowSuggestions(true)}
                className="w-full p-2 border rounded"
              />
              {showSuggestions && storedUsernames.length > 0 && (
                <div className="absolute z-10 w-full mt-1 bg-white border rounded-md shadow-lg">
                  {storedUsernames
                    .filter(stored => stored.toLowerCase().includes(username.toLowerCase()))
                    .map((stored, index) => (
                      <div
                        key={index}
                        className="px-4 py-2 cursor-pointer hover:bg-gray-100"
                        onClick={() => {
                          setUsername(stored)
                          setShowSuggestions(false)
                        }}
                      >
                        {stored}
                      </div>
                    ))}
                </div>
              )}
            </div>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                placeholder={`${platform === 'instagram' ? 'Instagram' : 'Facebook'} Password`}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full p-2 border rounded pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700"
              >
                {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
              </button>
            </div>
            <input
              type="number"
              placeholder="Number of Interactions"
              value={interactions}
              onChange={(e) => setInteractions(e.target.value)}
              className="w-full p-2 border rounded"
              min="1"
            />
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="localAccount"
                checked={isLocalAccount}
                onChange={(e) => setIsLocalAccount(e.target.checked)}
                className="w-4 h-4"
              />
              <label htmlFor="localAccount" className="text-sm text-gray-700">
                Local Account (Only interact with low engagement posts)
              </label>
            </div>
            <div className="flex gap-2">
              <Button
                onClick={() => {
                  setShowPassword(false);  // Hide password when launching bot
                  handleLaunchBot();
                }}
                disabled={isLoading || !username || !password}
                className="flex-1 bg-gradient-to-r from-[#2ECC71] to-[#82E0AA] hover:opacity-100 hover:shadow-lg hover:shadow-green-200/50 transition-all duration-200 transform hover:scale-[1.02] text-white font-bold"
              >
                {isLoading ? "Bot Running..." : "Launch Bot"}
              </Button>
              <Button
                onClick={handleStopBot}
                disabled={!isLoading}
                className="flex-1 bg-gradient-to-r from-[#FF0000] to-[#FF6666] hover:opacity-100 hover:shadow-lg hover:shadow-red-200/50 transition-all duration-200 transform hover:scale-[1.02] text-white font-bold"
              >
                Stop Bot
              </Button>
              <Button
                onClick={handleClearFields}
                className="flex-1 bg-gradient-to-r from-[#2980B9] to-[#7FB3D5] hover:opacity-100 hover:shadow-lg hover:shadow-blue-200/50 transition-all duration-200 transform hover:scale-[1.02] text-white font-bold"
              >
                Clear Fields
              </Button>
            </div>
          </div>
        </div>

        <div className="p-8">
          <h2 className="text-lg mb-4">Live Activity</h2>
          <div className="h-[400px] overflow-y-auto bg-gray-50 p-4 rounded">
            {output.map((line, i) => (
              <pre key={i} className="whitespace-pre-wrap text-sm">
                {line}
              </pre>
            ))}
          </div>
        </div>
      </div>

      <div className="flex-1 p-8">
        <h2 className="text-lg mb-4">Browser Preview</h2>
        <div className="bg-gray-50 h-[calc(100vh-8rem)] flex items-center justify-center rounded">
          <BrowserPreview isRunning={isLoading} />
        </div>
      </div>
    </div>
  )
}
