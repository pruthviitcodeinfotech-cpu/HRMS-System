import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import localizedFormat from "dayjs/plugin/localizedFormat";

dayjs.extend(relativeTime);
dayjs.extend(localizedFormat);

export const formatDate = (date: string | Date | number, formatStr = "DD MMM YYYY"): string => {
  return dayjs(date).format(formatStr);
};

export const formatRelativeTime = (date: string | Date | number): string => {
  return dayjs(date).fromNow();
};

export const getDaysInMonth = (year: number, month: number): number => {
  return dayjs(`${year}-${month}-01`).daysInMonth();
};
