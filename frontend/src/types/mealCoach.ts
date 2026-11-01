import { z } from "zod";

export const mealCritiqueSchema = z.object({
  overview: z.string(),
  add: z.array(z.string()),
  reduce: z.array(z.string()),
  caveat: z.string(),
});

export type MealCritique = z.infer<typeof mealCritiqueSchema>;

export interface MealChatMessage {
  role: "user" | "assistant";
  content: string;
  createdAt: string;
}

const chatReplySchema = z.object({ reply: z.string() });

export function parseChatReply(value: unknown): string | null {
  const parsed = chatReplySchema.safeParse(value);
  return parsed.success ? parsed.data.reply : null;
}
