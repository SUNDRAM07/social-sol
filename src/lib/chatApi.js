/**
 * Chat API Client
 * Handles communication with the chat backend endpoints
 */

import { apiUrl } from './api';
import { useAuthStore } from '../store/authStore';

/**
 * Send a message to the AI agent
 */
export async function sendChatMessage(content, conversationId = null, context = null) {
  const token = useAuthStore.getState().token;
  
  const response = await fetch(apiUrl('/chat/message'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({
      content,
      conversation_id: conversationId,
      context,
    }),
  });
  
  if (!response.ok) {
    throw new Error(`Chat request failed: ${response.status}`);
  }
  
  return response.json();
}

/**
 * Stream a response from the AI agent using fetch + ReadableStream
 * (More reliable than EventSource for authenticated requests)
 */
export async function streamChatMessage(content, conversationId, onChunk, onComplete, onError) {
  const token = useAuthStore.getState().token;
  
  try {
    const response = await fetch(apiUrl('/chat/stream'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        'Accept': 'text/event-stream',
      },
      body: JSON.stringify({
        content,
        conversation_id: conversationId,
      }),
    });
    
    if (!response.ok) {
      throw new Error(`Stream request failed: ${response.status}`);
    }
    
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    
    let fullContent = '';
    let intent = null;
    let actions = null;
    let newConversationId = conversationId;
    let buffer = '';
    
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) break;
      
      buffer += decoder.decode(value, { stream: true });
      
      // Process complete SSE messages
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            
            switch (data.type) {
              case 'intent':
                intent = data.data;
                break;
              case 'action':
                actions = data.data;
                break;
              case 'content':
                fullContent += data.data;
                onChunk(fullContent, intent, actions);
                break;
              case 'done':
                newConversationId = data.conversation_id || conversationId;
                onComplete({ 
                  content: fullContent, 
                  intent, 
                  actions, 
                  conversationId: newConversationId 
                });
                return;
              case 'error':
                onError(new Error(data.data));
                return;
            }
          } catch (e) {
            // Ignore parse errors for incomplete chunks
          }
        }
      }
    }
    
    // If we get here without 'done', still call onComplete
    onComplete({ content: fullContent, intent, actions, conversationId: newConversationId });
    
  } catch (error) {
    onError(error);
  }
}

/**
 * Get conversation history
 */
export async function getConversationHistory(conversationId) {
  const token = useAuthStore.getState().token;
  
  const response = await fetch(apiUrl(`/chat/history/${conversationId}`), {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  
  if (!response.ok) {
    throw new Error(`Failed to fetch history: ${response.status}`);
  }
  
  return response.json();
}

/**
 * List all conversations
 */
export async function listConversations(limit = 20) {
  const token = useAuthStore.getState().token;
  
  const response = await fetch(apiUrl(`/chat/conversations?limit=${limit}`), {
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  
  if (!response.ok) {
    throw new Error(`Failed to list conversations: ${response.status}`);
  }
  
  return response.json();
}

/**
 * Delete a conversation
 */
export async function deleteConversation(conversationId) {
  const token = useAuthStore.getState().token;
  
  const response = await fetch(apiUrl(`/chat/conversation/${conversationId}`), {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`,
    },
  });
  
  if (!response.ok) {
    throw new Error(`Failed to delete conversation: ${response.status}`);
  }
  
  return response.json();
}

