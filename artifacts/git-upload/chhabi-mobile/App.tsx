import {NavigationContainer} from '@react-navigation/native';
import {createBottomTabNavigator} from '@react-navigation/bottom-tabs';
import {createNativeStackNavigator} from '@react-navigation/native-stack';
import React from 'react';
import {StatusBar} from 'react-native';
import {SafeAreaProvider} from 'react-native-safe-area-context';
import {AuthProvider, useAuth} from './src/AuthContext';
import {AppIcon, LoadingScreen} from './src/components';
import {colors} from './src/theme';
import {RootStackParamList} from './src/types';
import {AttendanceScreen, DashboardScreen, GenericListScreen, LeaveCreateScreen, LeaveScreen, LoginScreen, MeetingCreateScreen, MeetingsScreen, MoreScreen, ProfileScreen} from './src/screens';

const Stack=createNativeStackNavigator<RootStackParamList>();const Tabs=createBottomTabNavigator();
const icons:Record<string,string>={Home:'home',Attendance:'finger-print',Leave:'calendar',Meetings:'videocam',More:'grid'};
function MainTabs(){return <Tabs.Navigator screenOptions={({route})=>({headerStyle:{backgroundColor:colors.navy},headerTintColor:'white',headerTitleStyle:{fontWeight:'800'},tabBarActiveTintColor:colors.blue,tabBarInactiveTintColor:'#98A2B3',tabBarStyle:{height:64,paddingBottom:8,paddingTop:7},tabBarIcon:({color,size})=><AppIcon name={icons[route.name]} color={color} size={size}/>})}><Tabs.Screen name="Home" component={DashboardScreen}/><Tabs.Screen name="Attendance" component={AttendanceScreen}/><Tabs.Screen name="Leave" component={LeaveScreen}/><Tabs.Screen name="Meetings" component={MeetingsScreen}/><Tabs.Screen name="More" component={MoreScreen}/></Tabs.Navigator>}
function Navigator(){const {session,loading}=useAuth();if(loading)return <LoadingScreen/>;return <NavigationContainer><StatusBar barStyle="light-content" backgroundColor={colors.navy}/><Stack.Navigator screenOptions={{headerStyle:{backgroundColor:colors.navy},headerTintColor:'white',headerTitleStyle:{fontWeight:'800'}}}>{session?<><Stack.Screen name="Main" component={MainTabs} options={{headerShown:false}}/><Stack.Screen name="ModuleList" component={GenericListScreen} options={({route})=>({title:route.params.title})}/><Stack.Screen name="LeaveCreate" component={LeaveCreateScreen} options={{title:'Request Leave'}}/><Stack.Screen name="MeetingCreate" component={MeetingCreateScreen} options={{title:'Create Meeting'}}/><Stack.Screen name="Profile" component={ProfileScreen}/></>:<Stack.Screen name="Login" component={LoginScreen} options={{headerShown:false}}/>}</Stack.Navigator></NavigationContainer>}
export default function App(){return <SafeAreaProvider><AuthProvider><Navigator/></AuthProvider></SafeAreaProvider>}
