import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { chatApi } from "@/lib/api";

export const useSendMessage = () => {
  return useMutation({
    mutationFn: (data: { message: string; session_id?: string | null }) =>
      chatApi.sendMessage(data).then(r => r.data),
  });
};

export const useChatSessions = () => {
  return useQuery({
    queryKey: ["chat-sessions"],
    queryFn: () => chatApi.getSessions().then(r => r.data),
  });
};

export const useChatSession = (token: string) => {
  return useQuery({
    queryKey: ["chat-session", token],
    queryFn: () => chatApi.getSession(token).then(r => r.data),
    enabled: !!token,
  });
};
