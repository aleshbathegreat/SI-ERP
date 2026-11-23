import api from "@/lib/api";

export type ListResponse<T> = T[] | { results: T[] };

export function unwrapList<T>(data: ListResponse<T>): T[] {
  return Array.isArray(data) ? data : data.results || [];
}

export async function listResource<T>(
  path: string,
  params?: Record<string, string | number | boolean | null | undefined>
): Promise<T[]> {
  const cleaned: Record<string, string | number | boolean> = {};
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v === null || v === undefined || v === "") continue;
      cleaned[k] = v;
    }
  }
  const { data } = await api.get<ListResponse<T>>(path, {
    params: Object.keys(cleaned).length ? cleaned : undefined,
  });
  return unwrapList(data);
}

export async function getResource<T>(path: string, id: number | string): Promise<T> {
  const base = path.endsWith("/") ? path : `${path}/`;
  const { data } = await api.get<T>(`${base}${id}/`);
  return data;
}

export async function createResource<T>(path: string, payload: unknown): Promise<T> {
  const { data } = await api.post<T>(path, payload);
  return data;
}

export async function updateResource<T>(
  path: string,
  id: number | string,
  payload: unknown
): Promise<T> {
  const { data } = await api.patch<T>(`${path}${id}/`, payload);
  return data;
}

export async function deleteResource(path: string, id: number | string): Promise<void> {
  await api.delete(`${path}${id}/`);
}

export async function bulkDeleteResource(path: string, ids: Array<number | string>): Promise<number> {
  const { data } = await api.post<{ deleted: number }>(`${path}bulk-delete/`, { ids });
  return data.deleted;
}
