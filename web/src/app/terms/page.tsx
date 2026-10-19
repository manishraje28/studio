import type { Metadata } from "next";
import LegalPage from "@/components/site/LegalPage";

export const metadata: Metadata = { title: "Terms and conditions | Studio" };

export default function Terms() {
  return (
    <LegalPage
      title="Terms and conditions"
      updated="19 October 2026"
      intro="These terms apply when you use this website or buy a Studio package. By starting a project you agree to them."
      sections={[
        { h: "The service", p: [
          "Studio builds websites using a team of AI agents with review by a human creative director. The package you choose lists what is included. Work outside the package is quoted in writing before it starts.",
        ] },
        { h: "Timeline", p: [
          "The 72 hour delivery time starts when you approve the visual direction and have sent the material we ask for, such as photos and opening hours. Waiting for your replies pauses the clock.",
        ] },
        { h: "Payment", p: [
          "The first brief chat is free. You pay the package price after you approve the visual direction and before the build starts. Prices include GST. Care plans are billed monthly and can be cancelled at any time before the next billing date.",
        ] },
        { h: "Revisions", p: [
          "Each package includes two revision rounds on the preview. A revision round is one set of comments sent together. Changes that add new pages or features are treated as new work.",
        ] },
        { h: "Your content", p: [
          "You confirm that you have the right to use the photos, logos and text you give us. We use them only for your project.",
        ] },
        { h: "Ownership", p: [
          "Once the package is paid in full, you own the website code, the design files and the copy we create for you. We may show the finished site in our portfolio unless you ask us not to.",
        ] },
        { h: "Refunds", p: [
          "If you do not approve the visual direction, you pay nothing. Once the build has started, payments are not refundable, but we will keep working on your revision rounds until the site matches the approved direction.",
        ] },
        { h: "Limits of liability", p: [
          "We test every site before launch, but we cannot promise that a website will bring a particular number of customers or sales. Our total liability for any claim is limited to the amount you paid for the package.",
        ] },
        { h: "Governing law", p: [
          "These terms are governed by the laws of India, and the courts of Pune, Maharashtra have jurisdiction.",
        ] },
        { h: "Contact", p: ["Questions about these terms go to hello@studio.example."] },
      ]}
    />
  );
}
