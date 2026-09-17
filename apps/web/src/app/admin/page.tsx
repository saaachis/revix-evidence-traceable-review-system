import type { Metadata } from "next";

import { PageHead } from "@/components/ui";

import AdminConsole from "./AdminConsole";

// noindex because this is an operations surface, not content. It is protected
// by the API rather than by obscurity, so keeping it out of search results is
// tidiness rather than security, but there is no reason for it to be indexed
// and every reason for it not to appear in a search for the product.
export const metadata: Metadata = {
  title: "Operations",
  description: "Connector health, ingestion runs, coverage and adjudication.",
  robots: { index: false, follow: false },
};

export default function AdminPage() {
  return (
    <>
      <PageHead title="Operations">
        Connector health, the ingestion log, where coverage is thin, and the listings the resolver
        would not place. Everything here is read from the same database the site serves from, and
        only one action on this page writes anything.
      </PageHead>
      <AdminConsole />
    </>
  );
}
