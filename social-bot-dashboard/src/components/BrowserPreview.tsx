'use client';

import { useEffect, useState } from 'react';

interface BrowserPreviewProps {
  isRunning: boolean;
}

export function BrowserPreview({ isRunning }: BrowserPreviewProps) {
  const [debuggerUrl, setDebuggerUrl] = useState<string | null>(null);

  useEffect(() => {
    async function connectToChrome() {
      if (isRunning) {
        try {
          // Wait a bit for Chrome to start up
          await new Promise(resolve => setTimeout(resolve, 2000));
          
          // Get available Chrome targets
          const response = await fetch('http://localhost:9222/json');
          const targets = await response.json();
          
          // Find the main target
          const mainTarget = targets.find((t: any) => t.type === 'page');
          if (mainTarget) {
            setDebuggerUrl(mainTarget.webSocketDebuggerUrl);
          }
        } catch (error) {
          console.error('Failed to connect to Chrome:', error);
        }
      } else {
        setDebuggerUrl(null);
      }
    }

    connectToChrome();
  }, [isRunning]);

  if (!debuggerUrl) {
    return (
      <div className="w-full h-full flex items-center justify-center bg-gray-100 rounded-lg">
        <p className="text-gray-500">Browser preview not available</p>
      </div>
    );
  }

  return (
    <div className="w-full h-full">
      <iframe
        src={`http://localhost:9222/devtools/inspector.html?ws=${encodeURIComponent(debuggerUrl.replace('ws://', ''))}`}
        className="w-full h-full rounded-lg border border-gray-200"
        sandbox="allow-same-origin allow-scripts"
      />
    </div>
  );
} 