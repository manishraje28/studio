# Studio

An autonomous AI agency: a team of AI agents researches, designs, writes, builds and tests a small business website in 72 hours, and the client watches the work live. Spec: `STUDIO_SPEC.md`.

## Constraints
- Zero cost: free tiers only (Gemini/Groq/OpenRouter free models or Ollama, Vercel, Render, Supabase, Upstash). The AI provider must stay swappable through one config setting.
- Build step by step; each step ends with something runnable that the user reviews.

## Design rules (non-negotiable)
The site must not look vibe-coded or AI-generated.
- No purple or blue-to-purple gradients. No gradient text.
- No pill-shaped buttons. Buttons use a small radius (4 to 8px).
- No fake reviews, testimonials, logos, metrics, user counts or customer counters. Show only true product facts (price, delivery time, what is included). Sample data must be labelled as an example.
- No vague hero copy. Say exactly what the product does, for whom, and the outcome.
- No emoji as icons. Use simple custom SVG icons.
- No em dashes in any copy.
- No over-the-top scroll animations, no custom cursor or cursor-follow effects.
- No AI-slop stock images or AI-generated filler copy.
- Every page has a real favicon, and there is no "Made with AI" badge.
- The site ships with a Privacy Policy page and a Terms and Conditions page.
- Check every page in a browser at desktop and mobile widths before calling it done.

## Chosen visual direction
"Clay Studio": warm, tactile 3D diorama of the agent team at work (React Three Fiber in the real app), editorial serif headings (Fraunces), clean sans body, rectangular buttons.
