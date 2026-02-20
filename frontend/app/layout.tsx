import "./globals.css";

export const metadata = {
  title: "AG-UI Project",
  description: "Project state UI with CopilotKit",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
