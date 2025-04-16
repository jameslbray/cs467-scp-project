import { useState } from 'react'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import { Button, Card } from '@sakura-ui/core'

function App() {
  const [count, setCount] = useState(0)

  return (
    <div className="min-h-screen w-full bg-gradient-to-b from-gray-50 to-gray-100 flex items-center justify-center">
      <div className="container mx-auto px-4 py-8">
        <Card className="w-full p-6 bg-white rounded-xl shadow-lg">
          <div className="flex justify-center space-x-8 mb-6">
            <a href="https://vite.dev" target="_blank" rel="noreferrer" className="hover:scale-110 transition-transform">
              <img src={viteLogo} className="h-16 w-16" alt="Vite logo" />
            </a>
            <a href="https://react.dev" target="_blank" rel="noreferrer" className="hover:scale-110 transition-transform">
              <img src={reactLogo} className="h-16 w-16 animate-spin-slow" alt="React logo" />
            </a>
          </div>
          
          <div className="text-center">
            <h1 className="text-2xl font-bold mb-4 text-blue-600">
              Vite + React + Tailwind + Sakura UI
            </h1>
            
            <span className="inline-block px-3 py-1 text-sm rounded-full bg-green-100 text-green-800 mb-6">
              Styled with Tailwind CSS
            </span>
            
            <Card className="p-4 mb-6 bg-gray-50">
              <Button 
                variant="primary" 
                size="lg" 
                className="mb-4"
                onClick={() => setCount((count) => count + 1)}
              >
                Count is {count}
              </Button>
              
              <p className="text-gray-600">
                Edit <code className="bg-gray-200 px-1 py-0.5 rounded text-sm">src/App.tsx</code> and save to test HMR
              </p>
            </Card>
            
            <p className="text-sm text-gray-500">
              Click on the Vite and React logos to learn more
            </p>
          </div>
        </Card>
      </div>
    </div>
  )
}

export default App
