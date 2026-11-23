import type { Metadata } from "next";
import { notFound } from "next/navigation";
import SiteFrame from "@/components/marketing/SiteFrame";
import { LEGAL_PAGES, legalBySlug } from "@/lib/legalPages";

type Props = { params: Promise<{ slug: string }> };

export function generateStaticParams() {
  return LEGAL_PAGES.map((page) => ({ slug: page.slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const page = legalBySlug(slug);
  if (!page) return { title: "Legal · SI-ERP" };
  return { title: `${page.title} · SI-ERP`, description: page.description };
}

export default async function LegalPage({ params }: Props) {
  const { slug } = await params;
  const page = legalBySlug(slug);
  if (!page) notFound();
  return (
    <SiteFrame>
      <article className="mk-legal">
        <h1>{page.title}</h1>
        <p className="mk-meta">Effective {page.updated} · SI Global (SIGBL)</p>
        {page.sections.map((section) => (
          <section key={section.heading}>
            <h2>{section.heading}</h2>
            {section.paragraphs.map((paragraph) => (
              <p key={paragraph} style={{ marginTop: 8 }}>{paragraph}</p>
            ))}
            {section.bullets ? (
              <ul>
                {section.bullets.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : null}
          </section>
        ))}
      </article>
    </SiteFrame>
  );
}
