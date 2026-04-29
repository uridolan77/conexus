import OpenAI from "openai";

async function main() {
  const baseURL = process.env.CONEXUS_BASE_URL ?? "http://localhost:8000/v1";
  const apiKey = process.env.CONEXUS_API_KEY; // project key: cx_live_...
  if (!apiKey) {
    throw new Error("Missing CONEXUS_API_KEY");
  }

  const model = process.env.CONEXUS_MODEL ?? "gpt-4o-mini";

  const client = new OpenAI({ apiKey, baseURL });

  console.log("== non-streaming ==");
  const resp = await client.chat.completions.create({
    model,
    messages: [{ role: "user", content: "Say hello from Conexus." }],
    temperature: 0.2,
    max_tokens: 64,
  });
  console.log(resp.choices[0]?.message?.content ?? "");

  console.log("\n== streaming ==");
  const stream = await client.chat.completions.create({
    model,
    messages: [{ role: "user", content: "Stream three short words." }],
    temperature: 0.2,
    max_tokens: 32,
    stream: true,
  });

  for await (const event of stream) {
    const delta = event.choices[0]?.delta;
    if (delta?.content) process.stdout.write(delta.content);
  }
  process.stdout.write("\n");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

