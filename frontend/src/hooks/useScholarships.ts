import { useQuery } from "@tanstack/react-query";
import { scholarshipApi } from "@/lib/api";

export const useScholarships = (params?: any) => {
  return useQuery({
    queryKey: ["scholarships", params],
    queryFn: () => scholarshipApi.list(params).then(r => r.data),
    staleTime: 5 * 60 * 1000,
  });
};

export const useScholarshipSearch = (params: any) => {
  return useQuery({
    queryKey: ["scholarship-search", params],
    queryFn: () => scholarshipApi.search(params).then(r => r.data),
    enabled: !!params.q,
    staleTime: 2 * 60 * 1000,
  });
};

export const useScholarship = (id: string) => {
  return useQuery({
    queryKey: ["scholarship", id],
    queryFn: () => scholarshipApi.getById(id).then(r => r.data),
    enabled: !!id,
  });
};

export const useUpcomingDeadlines = (days = 30) => {
  return useQuery({
    queryKey: ["upcoming-deadlines", days],
    queryFn: () => scholarshipApi.upcomingDeadlines(days).then(r => r.data),
    staleTime: 10 * 60 * 1000,
  });
};
