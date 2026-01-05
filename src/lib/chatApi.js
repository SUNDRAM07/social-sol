/**
 * Chat API Client
 * Handles communication with the chat backend endpoints
 */

import { getApiUrl } from './api';
import { useAuthStore } from '../store/authStore';

/**
 * Send a message to the AI agent
 */
export async function sendChatMessage(content, conversationId = null, context = null) {
  const token = useAuthStore.getState().token;
  
  const response = await fetch(getApiUrl('/chat/message'), {
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
 * Stream a response from the AI agent (SSE)
 */
export function streamChatMessage(conversationId, message, onChunk, onComplete, onError) {
  const token = useAuthStore.getState().token;
  const url = getApiUrl(`/chat/stream/${conversationId}?message=${encodeURIComponent(message)}`);
  
  const eventSource = new EventSource(url);
  let content = '';
  let intent = null;
  let actions = null;
  
  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'intent':
          intent = data.data;
          break;
        case 'action':
          actions = data.data;
          break;
        case 'content':
          content += data.data;
          onChunk(content, intent, actions);
          break;
        case 'done':
          eventSource.close();
          onComplete({ content, intent, actions });
          break;
        case 'error':
          eventSource.close();
          onError(new Error(data.data));
          break;
      }
    } catch (e) {
      console.error('SSE parse error:', e);
    }
  };
  
  eventSource.onerror = (error) => {
    eventSource.close();
    onError(error);
  };
  
  return () => eventSource.close();
}

/**
 * Get conversation history
 */
export async function getConversationHistory(conversationId) {
  const token = useAuthStore.getState().token;
  
  const response = await fetch(getApiUrl(`/chat/history/${conversationId}`), {
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
  
  const response = await fetch(getApiUrl(`/chat/conversations?limit=${limit}`), {
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
  
  const response = await fetch(getApiUrl(`/chat/conversation/${conversationId}`), {
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

