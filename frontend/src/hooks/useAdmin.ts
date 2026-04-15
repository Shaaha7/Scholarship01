import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { adminApi } from "@/lib/api";

export const useAdminStats = () => {
  return useQuery({
    queryKey: ["admin-stats"],
    queryFn: () => adminApi.stats().then(r => r.data),
    staleTime: 60 * 1000,
  });
};

export const useCreateScholarship = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: any) => adminApi.createScholarship(data).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["scholarships"] }); qc.invalidateQueries({ queryKey: ["admin-stats"] }); },
  });
};

export const useUploadPdf = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (formData: FormData) => adminApi.uploadPdf(formData).then(r => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["scholarships"] }); },
  });
};
