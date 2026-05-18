import { redirect } from "next/navigation";

export default function WhitepaperPage() {
  redirect("/whitepaper/index.html" as never);
}
