import { Injectable } from '@angular/core';
import { Observable, Subject } from 'rxjs';

export interface DifyStreamResponse {
  event: string;
  data: any;
}

@Injectable({
  providedIn: 'root'
})
export class DirectDifyService {
  
  private readonly DIFY_API_URL = 'https://api.dify.ai/v1';
  private readonly DIFY_API_KEY = 'app-KKtaMynVyn8tKbdV9VbbaeyR'; // Your Dify API key

  // Process prompt directly with Dify API
  async processPromptStreaming(
    prompt: string, 
    instructionId: string = 'default',
    conversationId: string = ''
  ): Promise<Observable<DifyStreamResponse>> {
    
    const subject = new Subject<DifyStreamResponse>();
    
    console.log('🚀 Starting direct Dify streaming for prompt...');
    
    try {
      const requestBody = {
        inputs: {},
        query: prompt,
        response_mode: 'streaming',
        conversation_id: conversationId,
        user: 'hawk-agent-user'
      };

      console.log('📤 Sending request to Dify:', requestBody);

      const response = await fetch(`${this.DIFY_API_URL}/chat-messages`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.DIFY_API_KEY}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        throw new Error(`Dify API error: ${response.status} ${response.statusText}`);
      }

      console.log('✅ Dify response received, starting stream processing...');

      // Process the streaming response
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body reader available');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      // Read the stream
      const processStream = async () => {
        try {
          while (true) {
            const { done, value } = await reader.read();
            
            if (done) {
              console.log('✅ Stream processing complete');
              subject.complete();
              break;
            }

            buffer += decoder.decode(value, { stream: true });
            
            // Process complete lines
            const lines = buffer.split('\n');
            buffer = lines.pop() || ''; // Keep incomplete line in buffer

            for (const line of lines) {
              if (line.trim() === '') continue;
              
              try {
                // Dify sends data in format: data: {json}
                if (line.startsWith('data: ')) {
                  const jsonStr = line.substring(6);
                  if (jsonStr.trim() === '[DONE]') {
                    console.log('✅ Dify stream finished');
                    continue;
                  }
                  
                  const data = JSON.parse(jsonStr);
                  
                  // Emit the streaming data
                  subject.next({
                    event: data.event || 'message',
                    data: data
                  });
                  
                  console.log('📨 Stream chunk received:', data.event);
                }
              } catch (parseError) {
                console.warn('⚠️ Failed to parse stream line:', line, parseError);
              }
            }
          }
        } catch (streamError) {
          console.error('❌ Stream processing error:', streamError);
          subject.error(streamError);
        }
      };

      // Start processing the stream
      processStream();

    } catch (error) {
      console.error('❌ Direct Dify request failed:', error);
      subject.error(error);
    }

    return subject.asObservable();
  }

  // Non-streaming version for simpler use cases
  async processPrompt(prompt: string, instructionId: string = 'default'): Promise<any> {
    console.log('🚀 Starting direct Dify request (non-streaming)...');
    
    try {
      const requestBody = {
        inputs: {},
        query: prompt,
        response_mode: 'blocking',
        user: 'hawk-agent-user'
      };

      const response = await fetch(`${this.DIFY_API_URL}/chat-messages`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.DIFY_API_KEY}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Dify API error: ${response.status} ${response.statusText} - ${errorText}`);
      }

      const result = await response.json();
      console.log('✅ Direct Dify request successful');
      return result;

    } catch (error) {
      console.error('❌ Direct Dify request failed:', error);
      throw error;
    }
  }

  // Test Dify connection
  async testConnection(): Promise<boolean> {
    try {
      console.log('🧪 Testing Dify API connection...');
      
      const testResponse = await this.processPrompt('Hello, this is a connection test.');
      console.log('✅ Dify connection test successful');
      return true;
      
    } catch (error) {
      console.error('❌ Dify connection test failed:', error);
      return false;
    }
  }
}