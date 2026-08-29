import {useFocusEffect, useNavigation} from '@react-navigation/native';
import React, {useCallback, useEffect, useState} from 'react';
import {
  Alert, FlatList, Image, KeyboardAvoidingView, Linking, Modal, Platform,
  Pressable, RefreshControl, ScrollView, StyleSheet, Text, TextInput, View,
} from 'react-native';
import {api, errorMessage, rowsOf} from './api';
import {useAuth} from './AuthContext';
import {AppIcon, Avatar, EmptyState, LoadingScreen, PrimaryButton, StatCard} from './components';
import {colors, shadow} from './theme';
import {collectAttendanceEvidence} from './secureAttendance';

export function LoginScreen() {
  const {signIn} = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [secure, setSecure] = useState(true);
  const [loading, setLoading] = useState(false);
  const submit = async () => {
    if (!username.trim() || !password) return Alert.alert('Required', 'Enter username and password.');
    setLoading(true);
    try { await signIn(username.trim(), password); }
    catch (error) { Alert.alert('Login failed', errorMessage(error)); }
    finally { setLoading(false); }
  };
  return <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={s.loginPage}>
    <View style={s.glowOne} /><View style={s.glowTwo} />
    <ScrollView contentContainerStyle={s.loginScroll} keyboardShouldPersistTaps="handled">
      <Image source={require('./assets/logo.jpeg')} style={s.logo} />
      <Text style={s.brand}>GEETA FORGETECH</Text><Text style={s.tagline}>Empowering IT Landscapes</Text>
      <View style={s.loginCard}>
        <Text style={s.loginTitle}>Welcome back</Text><Text style={s.subtle}>Sign in to your workplace</Text>
        <View style={s.inputWrap}><AppIcon name="person-outline" size={20} color={colors.muted} /><TextInput value={username} onChangeText={setUsername} placeholder="Username" placeholderTextColor="#98A2B3" autoCapitalize="none" style={s.input} /></View>
        <View style={s.inputWrap}><AppIcon name="lock-closed-outline" size={20} color={colors.muted} /><TextInput value={password} onChangeText={setPassword} placeholder="Password" placeholderTextColor="#98A2B3" secureTextEntry={secure} style={s.input} onSubmitEditing={submit} /><Pressable onPress={() => setSecure(!secure)}><AppIcon name={secure ? 'eye-outline' : 'eye-off-outline'} size={21} color={colors.muted} /></Pressable></View>
        <PrimaryButton title="Sign In" onPress={submit} loading={loading} />
      </View>
    </ScrollView>
  </KeyboardAvoidingView>;
}

export function DashboardScreen() {
  const {session} = useAuth(); const nav = useNavigation<any>();
  const [data, setData] = useState<any>(null); const [refreshing, setRefreshing] = useState(false);
  const load = async () => { try { setData((await api.get('/mobile/dashboard/')).data); } catch (e) { Alert.alert('Dashboard', errorMessage(e)); } };
  useFocusEffect(useCallback(() => { load(); }, []));
  if (!data) return <LoadingScreen />;
  const stats = data.stats;
  const trend = Array.isArray(data.attendance_trend) ? data.attendance_trend : [];
  const maxPresent = Math.max(1, ...trend.map((item: any) => Number(item.present) || 0));
  const todayLabel = new Date(`${data.date}T00:00:00`).toLocaleDateString(undefined, {weekday: 'long', day: 'numeric', month: 'short'});
  return <ScrollView style={s.page} contentContainerStyle={s.pageContent} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => {setRefreshing(true); await load(); setRefreshing(false);}} />}>
    <View style={s.hero}><View style={s.heroCopy}><Text style={s.eyebrow}>{todayLabel}</Text><Text style={s.hello}>Hello, {session?.profile.full_name?.split(' ')[0] || 'there'} 👋</Text><Text style={s.heroSub}>{session?.profile.company || 'Your workplace'}</Text></View><Pressable style={s.avatarRing} onPress={() => nav.navigate('Profile')}><Avatar uri={session?.profile.profile} name={session?.profile.full_name || 'U'} size={52} /></Pressable><View style={s.heroOrbOne}/><View style={s.heroOrbTwo}/></View>
    <Text style={s.sectionTitle}>Today overview</Text><View style={s.statsGrid}>
      <StatCard label="Employees" value={stats.employees} icon="people-outline" color={colors.blue} />
      <StatCard label="Present" value={stats.present_today} icon="checkmark-circle-outline" color={colors.success} />
      <StatCard label="Pending leaves" value={stats.pending_leaves} icon="calendar-outline" color={colors.warning} />
      <StatCard label="Meetings" value={stats.upcoming_meetings} icon="videocam-outline" color={colors.magenta} />
    </View>
    <View style={s.chartCard}>
      <View style={s.chartHeader}><View><Text style={s.chartTitle}>Attendance pulse</Text><Text style={s.chartSubtitle}>Last 7 days</Text></View><View style={s.rateBadge}><Text style={s.rateValue}>{data.attendance_rate || 0}%</Text><Text style={s.rateLabel}>today</Text></View></View>
      <View style={s.chartArea}>{trend.map((item: any, index: number) => <View key={`${item.date}-${index}`} style={s.barColumn}><Text style={s.barValue}>{item.present}</Text><View style={s.barTrack}><View style={[s.barFill, {height: `${Math.max(8, (Number(item.present) || 0) / maxPresent * 100)}%` as any}, index === trend.length - 1 && s.barFillToday]} /></View><Text style={[s.barLabel, index === trend.length - 1 && s.barLabelToday]}>{item.label}</Text></View>)}</View>
      {!trend.length && <Text style={s.chartEmpty}>Attendance trend will appear after the next sync.</Text>}
    </View>
    <Text style={s.sectionTitle}>Quick actions</Text><View style={s.quickRow}>
      <Quick icon="finger-print-outline" title="Attendance" onPress={() => nav.navigate('Attendance')} />
      <Quick icon="calendar-number-outline" title="Leave" onPress={() => nav.navigate('Leave')} />
      <Quick icon="videocam-outline" title="Meeting" onPress={() => nav.navigate('Meetings')} />
      <Quick icon="notifications-outline" title="Alerts" onPress={() => nav.navigate('ModuleList', {title: 'Notifications', endpoint: '/notifications/notifications/list/all'})} />
    </View>
  </ScrollView>;
}

function Quick({icon, title, onPress}: {icon: string; title: string; onPress: () => void}) {
  return <Pressable onPress={onPress} style={s.quick}><AppIcon name={icon} size={25} color={colors.cyan} /><Text style={s.quickText}>{title}</Text></Pressable>;
}

export function GenericListScreen({route}: any) {
  const {title, endpoint} = route.params; const [rows, setRows] = useState<any[]>([]); const [loading, setLoading] = useState(true); const [refreshing, setRefreshing] = useState(false); const [meta,setMeta]=useState<any>({}); const [editing,setEditing]=useState<any>(null); const [form,setForm]=useState<Record<string,any>>({}); const [saving,setSaving]=useState(false);
  const load = async () => { try {const data=(await api.get(endpoint)).data;setRows(rowsOf(data));setMeta(data?.schema?data:{});} catch (e) {Alert.alert(title, errorMessage(e));} finally {setLoading(false);} };
  // The endpoint is the navigation parameter that identifies this screen.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => {load();}, [endpoint]); if (loading) return <LoadingScreen />;
  const open=(item:any=null)=>{setEditing(item||{});const values:any={};(meta.schema||[]).forEach((field:any)=>values[field.name]=item?.[field.name]??'');setForm(values)};
  const save=async()=>{setSaving(true);try{if(editing?.id)await api.patch(`${endpoint}${editing.id}/`,form);else await api.post(endpoint,form);setEditing(null);await load();}catch(e){Alert.alert('Unable to save',errorMessage(e));}finally{setSaving(false)}};
  const remove=()=>Alert.alert('Delete record','This action cannot be undone.',[{text:'Cancel'},{text:'Delete',style:'destructive',onPress:async()=>{try{await api.delete(`${endpoint}${editing.id}/`);setEditing(null);await load();}catch(e){Alert.alert('Delete',errorMessage(e))}}}]);
  return <View style={s.page}><FlatList contentContainerStyle={s.listContent} data={rows} keyExtractor={(item, i) => String(item.id ?? i)} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async () => {setRefreshing(true); await load(); setRefreshing(false);}} />} ListEmptyComponent={<EmptyState title={`No ${title.toLowerCase()} found`} />} renderItem={({item}) => <RecordCard item={item} onPress={meta.can_change?()=>open(item):undefined} />} />{meta.can_add&&<Pressable style={s.fab} onPress={()=>open()}><AppIcon name="add" size={30}/></Pressable>}<Modal visible={editing!==null} animationType="slide" onRequestClose={()=>setEditing(null)}><View style={s.modalHeader}><Pressable onPress={()=>setEditing(null)}><Text style={s.modalClose}>Cancel</Text></Pressable><Text style={s.modalTitle}>{editing?.id?'Edit':'Create'} {title}</Text><View style={{width:50}}/></View><ScrollView style={s.page} contentContainerStyle={s.form}>{(meta.schema||[]).map((field:any)=><DynamicField key={field.name} field={field} value={form[field.name]} onChange={(value:any)=>setForm({...form,[field.name]:value})}/>)}<PrimaryButton title="Save" onPress={save} loading={saving}/>{editing?.id&&meta.can_delete&&<PrimaryButton title="Delete" danger onPress={remove}/>}</ScrollView></Modal></View>;
}

function DynamicField({field,value,onChange}:any){if(field.type==='boolean')return <Pressable style={s.booleanField} onPress={()=>onChange(!value)}><Text style={s.label}>{field.label}</Text><Text style={s.booleanValue}>{value?'✅ Yes':'⬜ No'}</Text></Pressable>;const options=field.choices?.length?field.choices:field.options;if(options?.length)return <View style={s.field}><Text style={s.label}>{field.label}{field.required?' *':''}</Text><ScrollView horizontal showsHorizontalScrollIndicator={false}>{options.map((option:any)=><Pressable key={String(option.value)} onPress={()=>onChange(option.value)} style={[s.choice,String(value)===String(option.value)&&s.choiceActive]}><Text style={String(value)===String(option.value)?s.choiceTextActive:s.choiceText}>{option.label}</Text></Pressable>)}</ScrollView></View>;return <Field label={`${field.label}${field.required?' *':''}`} value={value==null?'':String(value)} setValue={onChange} placeholder={field.type==='date'?'YYYY-MM-DD':field.type==='datetime'?'YYYY-MM-DDTHH:mm:ss':field.label} multiline={false}/>}

function RecordCard({item,onPress}: {item: any;onPress?:()=>void}) {
  const title = item.display || item.full_name || item.title || item.name || item.employee || item.subject || item.verbose_name || item.username || `Record #${item.id ?? ''}`;
  const ignored = new Set(['id','title','name','full_name','employee_profile','profile','file']);
  const details = Object.entries(item).filter(([k,v]) => !ignored.has(k) && v !== null && typeof v !== 'object').slice(0,4);
  return <Pressable onPress={onPress} style={s.record}><Text style={s.recordTitle}>{String(title)}</Text>{details.map(([key,value]) => <View key={key} style={s.detailRow}><Text style={s.detailKey}>{key.replaceAll('_',' ')}</Text><Text numberOfLines={2} style={s.detailValue}>{String(value)}</Text></View>)}</Pressable>;
}

export function AttendanceScreen() {
  const [records, setRecords] = useState<any[]>([]); const [busy, setBusy] = useState(false); const [refreshing, setRefreshing] = useState(false);
  const load = async () => {try {setRecords(rowsOf((await api.get('/attendance/my-attendance/')).data));} catch(e){Alert.alert('Attendance',errorMessage(e));}};
  useFocusEffect(useCallback(() => {load();}, []));
  const action = async (type: 'clock-in'|'clock-out') => {setBusy(true); try {const evidence=await collectAttendanceEvidence();await api.post('/mobile/secure-attendance/',{action:type,...evidence}); Alert.alert('Success', type === 'clock-in' ? 'Biometric and workplace location verified; live selfie saved. Clocked in.' : 'Verified and clocked out.'); await load();} catch(e){Alert.alert('Attendance',errorMessage(e));} finally{setBusy(false);}};
  return <View style={s.page}><View style={s.attendanceHero}><AppIcon name="finger-print" size={54} color={colors.cyan}/><Text style={s.attendanceTitle}>Mark Attendance</Text><Text style={s.heroSub}>Your secure workplace attendance</Text><View style={s.actionRow}><PrimaryButton title="Clock In" onPress={() => action('clock-in')} loading={busy}/><PrimaryButton title="Clock Out" onPress={() => action('clock-out')} loading={busy} danger/></View></View><FlatList contentContainerStyle={s.listContent} data={records} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={async()=>{setRefreshing(true);await load();setRefreshing(false);}}/>} keyExtractor={(x,i)=>String(x.id??i)} ListHeaderComponent={<Text style={s.sectionTitle}>Attendance history</Text>} ListEmptyComponent={<EmptyState/>} renderItem={({item})=><RecordCard item={item}/>}/></View>;
}

export function LeaveScreen() {
  const nav=useNavigation<any>(); const [rows,setRows]=useState<any[]>([]); const [loading,setLoading]=useState(true);
  const load=async()=>{try{setRows(rowsOf((await api.get('/leave/user-request/')).data));}catch(e){Alert.alert('Leave',errorMessage(e));}finally{setLoading(false);}};
  useFocusEffect(useCallback(()=>{load();},[])); if(loading)return <LoadingScreen/>;
  return <View style={s.page}><FlatList contentContainerStyle={s.listContent} data={rows} keyExtractor={(x,i)=>String(x.id??i)} ListEmptyComponent={<EmptyState title="No leave requests"/>} renderItem={({item})=><RecordCard item={item}/>}/><Pressable style={s.fab} onPress={()=>nav.navigate('LeaveCreate')}><AppIcon name="add" size={30} color="white"/></Pressable></View>;
}

export function LeaveCreateScreen({navigation}:any) {
  const [leaveTypes,setLeaveTypes]=useState<any[]>([]); const [type,setType]=useState(''); const [start,setStart]=useState(''); const [end,setEnd]=useState(''); const [description,setDescription]=useState(''); const [busy,setBusy]=useState(false);
  useEffect(()=>{api.get('/leave/available-leave/').then(r=>setLeaveTypes(rowsOf(r.data))).catch(()=>{});},[]);
  const submit=async()=>{if(!type||!start||!end)return Alert.alert('Required','Select leave type and enter dates in YYYY-MM-DD.');setBusy(true);try{await api.post('/leave/user-request/',{leave_type_id:type,start_date:start,end_date:end,description});Alert.alert('Success','Leave request submitted.');navigation.goBack();}catch(e){Alert.alert('Leave request',errorMessage(e));}finally{setBusy(false);}};
  return <ScrollView style={s.page} contentContainerStyle={s.form}><Text style={s.label}>Leave type</Text><ScrollView horizontal showsHorizontalScrollIndicator={false}>{leaveTypes.map(x=><Pressable key={x.id} onPress={()=>setType(String(x.id))} style={[s.choice,type===String(x.id)&&s.choiceActive]}><Text style={type===String(x.id)?s.choiceTextActive:s.choiceText}>{x.leave_type_id?.name||x.name||`Type ${x.id}`}</Text></Pressable>)}</ScrollView><Field label="Start date" value={start} setValue={setStart} placeholder="YYYY-MM-DD"/><Field label="End date" value={end} setValue={setEnd} placeholder="YYYY-MM-DD"/><Field label="Reason" value={description} setValue={setDescription} placeholder="Reason for leave" multiline/><PrimaryButton title="Submit Request" onPress={submit} loading={busy}/></ScrollView>;
}

export function MeetingsScreen() {
  const nav=useNavigation<any>(); const [rows,setRows]=useState<any[]>([]); const [loading,setLoading]=useState(true);
  const load=async()=>{try{setRows(rowsOf((await api.get('/collaboration/meetings/')).data));}catch(e){Alert.alert('Meetings',errorMessage(e));}finally{setLoading(false);}};
  useFocusEffect(useCallback(()=>{load();},[])); if(loading)return <LoadingScreen/>;
  return <View style={s.page}><FlatList contentContainerStyle={s.listContent} data={rows} keyExtractor={x=>String(x.id)} ListEmptyComponent={<EmptyState title="No meetings scheduled"/>} renderItem={({item})=><View style={s.record}><View style={s.meetingHead}><AppIcon name="videocam" size={22} color={colors.magenta}/><Text style={[s.recordTitle,{flex:1}]}>{item.title}</Text></View><Text style={s.subtle}>{new Date(item.date).toLocaleString()}</Text><Text numberOfLines={2} style={s.meetingDescription}>{item.description}</Text><PrimaryButton title="Join / Start" onPress={()=>Linking.openURL(item.join_url)}/></View>}/><Pressable style={s.fab} onPress={()=>nav.navigate('MeetingCreate')}><AppIcon name="add" size={30} color="white"/></Pressable></View>;
}

export function MeetingCreateScreen({navigation}:any) {
  const [title,setTitle]=useState(''); const [description,setDescription]=useState(''); const [date,setDate]=useState(''); const [busy,setBusy]=useState(false);
  const submit=async()=>{if(!title||!date)return Alert.alert('Required','Enter title and ISO date/time.');setBusy(true);try{await api.post('/collaboration/meetings/',{title,description,date:new Date(date).toISOString(),meeting_type:'internal',provider:'internal',allow_chat:true,allow_captions:true,allow_recording:true,employee_id:[]});Alert.alert('Success','Meeting scheduled.');navigation.goBack();}catch(e){Alert.alert('Meeting',errorMessage(e));}finally{setBusy(false);}};
  return <ScrollView style={s.page} contentContainerStyle={s.form}><Field label="Meeting title" value={title} setValue={setTitle} placeholder="Weekly review"/><Field label="Description" value={description} setValue={setDescription} multiline placeholder="Agenda and notes"/><Field label="Start date & time" value={date} setValue={setDate} placeholder="2026-08-05T10:30:00+05:30"/><PrimaryButton title="Schedule Meeting" onPress={submit} loading={busy}/></ScrollView>;
}

function Field({label,value,setValue,placeholder,multiline}:any){return <View style={s.field}><Text style={s.label}>{label}</Text><TextInput style={[s.textField,multiline&&{height:110,textAlignVertical:'top'}]} value={value} onChangeText={setValue} placeholder={placeholder} placeholderTextColor="#98A2B3" multiline={multiline}/></View>}

export function MoreScreen(){const nav=useNavigation<any>();const [sections,setSections]=useState<any[]>([]);const [loading,setLoading]=useState(true);const load=useCallback(async()=>{try{setSections((await api.get('/mobile/modules/')).data.sections||[])}catch(e){Alert.alert('Modules',errorMessage(e))}finally{setLoading(false)}},[]);useFocusEffect(useCallback(()=>{load()},[load]));if(loading)return <LoadingScreen/>;return <ScrollView style={s.page} contentContainerStyle={s.moreContent}>{sections.map(section=><View key={section.key}><View style={s.sectionHeading}><Text style={s.sectionEmoji}>{section.icon}</Text><Text style={s.sectionTitle}>{section.title}</Text></View><View style={s.moreGrid}>{section.modules.map((item:any)=><Pressable key={item.key} style={s.moduleCard} onPress={()=>nav.navigate('ModuleList',{title:item.title,endpoint:item.endpoint})}><Text style={s.moduleEmoji}>{item.icon}</Text><Text style={s.moduleTitle}>{item.title}</Text><AppIcon name="forward" size={20}/></Pressable>)}</View></View>)}</ScrollView>}

export function ProfileScreen(){const {session,signOut}=useAuth();const p=session!.profile;return <ScrollView style={s.page} contentContainerStyle={s.profile}><Avatar uri={p.profile} name={p.full_name} size={92}/><Text style={s.profileName}>{p.full_name}</Text><Text style={s.subtle}>{p.job_position} · {p.department}</Text><View style={s.profileCard}><Info icon="business-outline" label="Company" value={p.company}/><Info icon="mail-outline" label="Email" value={p.email}/><Info icon="call-outline" label="Phone" value={p.phone}/><Info icon="id-card-outline" label="Badge" value={p.badge_id}/></View><PrimaryButton title="Sign Out" danger onPress={()=>Alert.alert('Sign out','Do you want to sign out?',[{text:'Cancel'},{text:'Sign out',style:'destructive',onPress:signOut}])}/><Text style={s.version}>Geeta Forgetech Mobile · 1.0.0</Text></ScrollView>}
function Info({icon,label,value}:any){return <View style={s.info}><AppIcon name={icon} size={22} color={colors.blue}/><View><Text style={s.detailKey}>{label}</Text><Text style={s.infoValue}>{value||'-'}</Text></View></View>}

const s=StyleSheet.create({
  page:{flex:1,backgroundColor:colors.background},pageContent:{padding:18,paddingBottom:35},loginPage:{flex:1,backgroundColor:colors.navy},loginScroll:{flexGrow:1,justifyContent:'center',padding:24},glowOne:{position:'absolute',width:280,height:280,borderRadius:140,backgroundColor:'#123B9166',top:-90,right:-90},glowTwo:{position:'absolute',width:220,height:220,borderRadius:110,backgroundColor:'#D000FF33',bottom:-80,left:-80},logo:{width:118,height:118,borderRadius:59,alignSelf:'center',borderWidth:3,borderColor:colors.cyan},brand:{color:'white',fontSize:24,fontWeight:'900',letterSpacing:2,textAlign:'center',marginTop:16},tagline:{color:colors.cyan,textAlign:'center',fontWeight:'700',marginTop:4},loginCard:{backgroundColor:'white',borderRadius:24,padding:22,marginTop:30,...shadow},loginTitle:{fontSize:24,fontWeight:'900',color:colors.navy},subtle:{color:colors.muted,marginTop:4},inputWrap:{height:52,borderWidth:1,borderColor:colors.border,borderRadius:14,flexDirection:'row',alignItems:'center',paddingHorizontal:14,marginVertical:8},input:{flex:1,color:colors.text,fontSize:15,marginLeft:10},hero:{backgroundColor:colors.navy,borderRadius:26,padding:22,flexDirection:'row',alignItems:'center',justifyContent:'space-between',marginBottom:22,overflow:'hidden',minHeight:142,...shadow},heroCopy:{zIndex:2,maxWidth:'75%'},eyebrow:{color:colors.cyan,fontSize:11,fontWeight:'800',textTransform:'uppercase',letterSpacing:1.2,marginBottom:7},hello:{color:'white',fontSize:24,fontWeight:'900'},heroSub:{color:'#B9C6EC',marginTop:6},avatarRing:{zIndex:2,borderWidth:2,borderColor:'#FFFFFF55',padding:3,borderRadius:32},heroOrbOne:{position:'absolute',width:120,height:120,borderRadius:60,backgroundColor:'#123B91',right:-35,top:-48},heroOrbTwo:{position:'absolute',width:90,height:90,borderRadius:45,backgroundColor:'#D000FF25',left:-28,bottom:-45},sectionTitle:{fontSize:18,fontWeight:'900',color:colors.navy,marginBottom:13,marginTop:4},statsGrid:{flexDirection:'row',flexWrap:'wrap',justifyContent:'space-between'},chartCard:{backgroundColor:'white',borderRadius:22,padding:18,marginBottom:22,...shadow},chartHeader:{flexDirection:'row',justifyContent:'space-between',alignItems:'center'},chartTitle:{fontSize:17,fontWeight:'900',color:colors.navy},chartSubtitle:{fontSize:12,color:colors.muted,marginTop:3},rateBadge:{backgroundColor:'#EAFBF3',borderRadius:14,paddingHorizontal:12,paddingVertical:7,alignItems:'center'},rateValue:{color:colors.success,fontWeight:'900',fontSize:15},rateLabel:{color:colors.success,fontSize:9,textTransform:'uppercase',fontWeight:'700'},chartArea:{height:150,flexDirection:'row',alignItems:'flex-end',justifyContent:'space-between',marginTop:15},barColumn:{height:'100%',width:'11%',alignItems:'center',justifyContent:'flex-end'},barValue:{fontSize:10,color:colors.muted,marginBottom:5,fontWeight:'700'},barTrack:{height:104,width:18,borderRadius:9,backgroundColor:'#EEF2F8',justifyContent:'flex-end',overflow:'hidden'},barFill:{width:'100%',backgroundColor:'#8AA7E8',borderRadius:9,minHeight:8},barFillToday:{backgroundColor:colors.cyan},barLabel:{fontSize:10,color:colors.muted,fontWeight:'700',marginTop:7},barLabelToday:{color:colors.blue},chartEmpty:{color:colors.muted,textAlign:'center',paddingVertical:20},quickRow:{flexDirection:'row',justifyContent:'space-between'},quick:{width:'23%',backgroundColor:'white',borderRadius:18,paddingVertical:16,alignItems:'center',borderWidth:1,borderColor:'#EDF1F7',...shadow},quickText:{fontSize:10,color:colors.navy,fontWeight:'800',marginTop:7},listContent:{padding:16,paddingBottom:90,flexGrow:1},record:{backgroundColor:'white',borderRadius:18,padding:17,marginBottom:12,...shadow},recordTitle:{fontSize:16,fontWeight:'800',color:colors.navy,marginBottom:8},detailRow:{flexDirection:'row',justifyContent:'space-between',borderTopWidth:1,borderTopColor:'#F2F4F7',paddingVertical:7},detailKey:{fontSize:11,color:colors.muted,textTransform:'capitalize'},detailValue:{fontSize:12,color:colors.text,maxWidth:'58%',textAlign:'right'},attendanceHero:{backgroundColor:colors.navy,padding:24,alignItems:'center'},attendanceTitle:{fontSize:22,fontWeight:'900',color:'white',marginTop:8},actionRow:{flexDirection:'row',gap:12,marginTop:20},meetingHead:{flexDirection:'row',alignItems:'center',gap:10},meetingDescription:{color:colors.text,marginVertical:12},fab:{position:'absolute',right:22,bottom:24,width:58,height:58,borderRadius:29,backgroundColor:colors.blue,alignItems:'center',justifyContent:'center',...shadow},form:{padding:20,gap:13},field:{marginBottom:5},label:{fontWeight:'800',color:colors.navy,marginBottom:8},textField:{borderWidth:1,borderColor:colors.border,borderRadius:14,paddingHorizontal:15,minHeight:52,backgroundColor:'white',color:colors.text},choice:{paddingHorizontal:15,paddingVertical:10,borderRadius:18,backgroundColor:'white',borderWidth:1,borderColor:colors.border,marginRight:8},choiceActive:{backgroundColor:colors.blue,borderColor:colors.blue},choiceText:{color:colors.text},choiceTextActive:{color:'white',fontWeight:'700'},moreContent:{padding:16},moreGrid:{flexDirection:'row',flexWrap:'wrap',justifyContent:'space-between'},sectionHeading:{flexDirection:'row',alignItems:'center',gap:9,marginTop:12},sectionEmoji:{fontSize:22},moduleCard:{width:'48%',backgroundColor:'white',padding:16,borderRadius:18,marginBottom:14,...shadow},moduleEmoji:{fontSize:30},moduleTitle:{fontWeight:'800',color:colors.navy,fontSize:14,marginVertical:11},modalHeader:{height:62,backgroundColor:colors.navy,flexDirection:'row',alignItems:'center',justifyContent:'space-between',paddingHorizontal:16},modalClose:{color:colors.cyan,fontWeight:'700'},modalTitle:{color:'white',fontWeight:'900',fontSize:16},booleanField:{backgroundColor:'white',borderRadius:14,padding:15,flexDirection:'row',justifyContent:'space-between'},booleanValue:{color:colors.text,fontWeight:'700'},profile:{padding:24,alignItems:'center'},profileName:{fontSize:24,fontWeight:'900',color:colors.navy,marginTop:13},profileCard:{backgroundColor:'white',borderRadius:20,padding:18,width:'100%',marginVertical:24,...shadow},info:{flexDirection:'row',gap:14,alignItems:'center',paddingVertical:12,borderBottomWidth:1,borderBottomColor:'#F2F4F7'},infoValue:{fontWeight:'700',color:colors.text,marginTop:3},version:{color:colors.muted,fontSize:11,marginTop:25},
});
