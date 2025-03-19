import { NextResponse } from 'next/server';
import { spawn } from 'child_process';

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { platform, username, password, interactions, isLocalAccount } = body;

    // Create a new TransformStream for streaming
    const stream = new TransformStream();
    const writer = stream.writable.getWriter();
    const encoder = new TextEncoder();

    // Set environment variables for unbuffered output
    const env = {
      ...process.env,
      PYTHONUNBUFFERED: "1"
    };

    // Spawn Python process with unbuffered output
    const pythonProcess = spawn('C:\\Users\\hcmal\\AppData\\Local\\Microsoft\\WindowsApps\\python.exe', [
      '-u',  // Force unbuffered output
      'C:\\Users\\hcmal\\OneDrive\\Desktop\\insta bot 2\\instagram_bot.py',
      '--username', username,
      '--password', password,
      '--interactions', interactions.toString(),
      '--local-account', isLocalAccount ? 'true' : 'false'
    ], {
      env,
      windowsHide: true
    });

    // Handle early client disconnection
    req.signal.addEventListener('abort', () => {
      pythonProcess.kill();
      writer.close().catch(() => {
        // Ignore close errors as the stream might already be closed
      });
    });

    // Stream stdout data
    pythonProcess.stdout.on('data', async (data) => {
      try {
        const lines = data.toString().split('\n').filter(line => line.trim());
        for (const line of lines) {
          await writer.write(encoder.encode(line + '\n')).catch(() => {
            // Ignore write errors if the stream is closed
            pythonProcess.kill();
          });
        }
      } catch (error) {
        // Log the error but don't throw - this prevents unhandled rejection warnings
        console.error('Error writing to stream:', error);
      }
    });

    // Stream stderr data
    pythonProcess.stderr.on('data', async (data) => {
      try {
        await writer.write(encoder.encode('ERROR: ' + data.toString() + '\n')).catch(() => {
          // Ignore write errors if the stream is closed
          pythonProcess.kill();
        });
      } catch (error) {
        console.error('Error writing to stream:', error);
      }
    });

    // Handle process completion
    pythonProcess.on('close', async (code) => {
      try {
        if (code !== 0) {
          await writer.write(encoder.encode(`Process exited with code ${code}\n`)).catch(() => {
            // Ignore write errors if the stream is closed
          });
        }
        await writer.close().catch(() => {
          // Ignore close errors as the stream might already be closed
        });
      } catch (error) {
        console.error('Error closing stream:', error);
      }
    });

    return new Response(stream.readable, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });

  } catch (error) {
    console.error('Bot API error:', error);
    return NextResponse.json({ 
      success: false, 
      error: 'Internal server error: ' + error 
    }, { status: 500 });
  }
} 