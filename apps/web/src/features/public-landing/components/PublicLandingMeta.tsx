"use client";

import { useEffect } from "react";

const SEO_CONFIG = {
  title: "ValuePact — Business Value Platform for Enterprise Revenue Teams",
  description:
    "Transform account intelligence into defensible value models, benchmarked ROI analyses, and executive-ready deliverables. Built for value consultants, account executives, and revenue teams.",
  ogTitle:
    "ValuePact — Turn account evidence into a business case your buyer can defend.",
  ogDescription:
    "The business value platform that brings intelligence, modeling, benchmarking, and governance into one workflow.",
  canonicalUrl: "https://valuepact.ai",
} as const;

const structuredData = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "ValuePact",
  applicationCategory: "BusinessApplication",
  description: SEO_CONFIG.description,
  url: SEO_CONFIG.canonicalUrl,
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "USD",
  },
};

export function PublicLandingMeta() {
  useEffect(() => {
    document.title = SEO_CONFIG.title;

    const metaTags: { name?: string; property?: string; content: string }[] = [
      { name: "description", content: SEO_CONFIG.description },
      { property: "og:title", content: SEO_CONFIG.ogTitle },
      {
        property: "og:description",
        content: SEO_CONFIG.ogDescription,
      },
      { property: "og:type", content: "website" },
      { property: "og:url", content: SEO_CONFIG.canonicalUrl },
      { name: "twitter:card", content: "summary_large_image" },
      { name: "twitter:title", content: SEO_CONFIG.ogTitle },
      {
        name: "twitter:description",
        content: SEO_CONFIG.ogDescription,
      },
    ];

    metaTags.forEach(({ name, property, content }) => {
      const selector = name
        ? `meta[name="${name}"]`
        : `meta[property="${property}"]`;
      let tag = document.querySelector(selector) as HTMLMetaElement | null;
      if (!tag) {
        tag = document.createElement("meta");
        if (name) tag.setAttribute("name", name);
        if (property) tag.setAttribute("property", property);
        document.head.appendChild(tag);
      }
      tag.content = content;
    });

    const existingScript = document.querySelector(
      'script[type="application/ld+json"]'
    );
    if (existingScript) existingScript.remove();
    const script = document.createElement("script");
    script.type = "application/ld+json";
    script.textContent = JSON.stringify(structuredData);
    document.head.appendChild(script);

    return () => {
      metaTags.forEach(({ name, property }) => {
        const selector = name
          ? `meta[name="${name}"]`
          : `meta[property="${property}"]`;
        const tag = document.querySelector(selector);
        if (tag) tag.remove();
      });
      const ldScript = document.querySelector(
        'script[type="application/ld+json"]'
      );
      if (ldScript) ldScript.remove();
    };
  }, []);

  return null;
}
