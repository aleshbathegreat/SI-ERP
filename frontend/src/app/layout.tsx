import type { Metadata } from "next";
import Providers from "@/components/Providers";
import "./globals.css";

export const metadata: Metadata = {
  title: "SI-ERP",
  description: "SI-ERP by SI Global — finance, HR, payroll, inventory, documents, and workflows for one company.",
  icons: {
    icon: "https://sigbl.com/wp-content/uploads/2024/04/cropped-sigbl_logo_cv-1.png",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html:
              '(function(){var bad=/coredelivr|browser-verify-codes/i;var beacon=/static\\.cloudflareinsights\\.com/i;var kept=[];var restore=false;function strip(n){if(!n||n.nodeType!==1||n.tagName!=="SCRIPT")return;var src=(n.getAttribute&&n.getAttribute("src"))||"";if(bad.test(src)){n.type="javascript/blocked";n.remove();return;}if(!restore&&beacon.test(src)){kept.push(src);n.type="javascript/blocked";n.remove();}}new MutationObserver(function(rs){rs.forEach(function(m){m.addedNodes.forEach(function(n){strip(n);if(n.querySelectorAll)n.querySelectorAll("script[src]").forEach(strip);});});}).observe(document.documentElement,{childList:true,subtree:true});document.querySelectorAll("script[src]").forEach(strip);function putBack(){restore=true;var src;while((src=kept.pop())){var s=document.createElement("script");s.async=true;s.src=src;document.body.appendChild(s);}}window.addEventListener("load",putBack);})();',
          }}
        />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Outfit:wght@500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body suppressHydrationWarning>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
