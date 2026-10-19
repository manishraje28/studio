import type { Metadata } from "next";
import LegalPage from "@/components/site/LegalPage";

export const metadata: Metadata = { title: "Privacy policy | Studio" };

export default function Privacy() {
  return (
    <LegalPage
      title="Privacy policy"
      updated="19 October 2026"
      intro="This policy explains what information Studio collects when you use this website and our services, why we collect it, and the choices you have. It is written to follow India's Digital Personal Data Protection Act, 2023."
      sections={[
        { h: "What we collect", p: [
          "Information you give us: your name, email address, phone number, business details, the answers you give in the brief chat, and any files or photos you upload for your project.",
          "Information about your business that is already public, such as your website, Google Business reviews and social media pages. Our research agent reads these only to prepare your project.",
          "Basic technical data when you visit the site, such as browser type and pages viewed. We do not use advertising trackers.",
        ] },
        { h: "How we use it", p: [
          "To run your project: research, design, writing, building, testing and deploying your website.",
          "To contact you about your project, invoices and support.",
          "We do not sell your data, and we do not use your files or brief to train AI models.",
        ] },
        { h: "AI processing", p: [
          "Your brief and project files are sent to third party AI model providers to generate research, designs, copy and code. These providers process the data on our behalf and are not allowed to use it for their own purposes under the terms we use them on.",
        ] },
        { h: "Who we share it with", p: [
          "Service providers that help us run Studio, such as hosting, database, email and payment providers, only as needed to deliver the service.",
          "Authorities, if the law requires it.",
        ] },
        { h: "How long we keep it", p: [
          "We keep project data for as long as your project or Care plan is active, and for up to 12 months after that so you can ask for changes. Invoices are kept as long as tax law requires. You can ask us to delete your data earlier.",
        ] },
        { h: "Your rights", p: [
          "You can ask to see, correct or delete your personal data, or withdraw your consent, by writing to hello@studio.example. We reply within 30 days.",
        ] },
        { h: "Security", p: [
          "Files are encrypted at rest and in transit. Each client's data is kept separate, and access is limited to the people and agents working on that project.",
        ] },
        { h: "Changes and contact", p: [
          "If we change this policy we will update the date above and tell active clients by email. Questions go to hello@studio.example.",
        ] },
      ]}
    />
  );
}
