export type Profile = {
  id: number;
  username: string;
  full_name: string;
  email?: string;
  phone?: string;
  profile?: string | null;
  company?: string;
  company_id?: number;
  department?: string;
  job_position?: string;
  badge_id?: string;
};

export type Modules = Record<string, boolean>;

export type Session = {
  access: string;
  refresh: string;
  profile: Profile;
  permissions: string[];
  modules: Modules;
};

export type RootStackParamList = {
  Login: undefined;
  Main: undefined;
  ModuleList: {title: string; endpoint: string};
  LeaveCreate: undefined;
  MeetingCreate: undefined;
  Profile: undefined;
};
