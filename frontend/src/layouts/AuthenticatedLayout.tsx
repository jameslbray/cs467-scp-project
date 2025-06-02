import type React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import DarkModeToggle from '../components/DarkModeToggle';
import FriendsList from '../components/FriendsList';
import NotificationBell from '../components/NotificationsList';
import SearchUsers from '../components/SearchUsers';
import UserProfileMenu from '../components/UserProfileMenu';
import { useAuth } from '../contexts/auth/authContext';
import { FriendsProvider, useFriends } from '../contexts/friends/FriendsContext';

const AuthenticatedLayoutInner: React.FC = () => {
	const { isAuthenticated, isLoading } = useAuth();
	const { friends } = useFriends();

	if (isLoading) {
		return (
			<div className='flex items-center justify-center min-h-screen bg-gray-100 dark:bg-gray-900'>
				<div className='animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500' />
			</div>
		);
	}

	if (!isAuthenticated) {
		return <Navigate to='/login' replace />;
	}

	return (
		<div className='min-h-screen bg-gray-100 dark:bg-gray-900'>
			{/* Header */}
			<header className='bg-white dark:bg-gray-800 shadow'>
				<div className='max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4'>
					<div className='flex justify-between items-center'>
						<h1 className='text-2xl font-bold text-gray-900 dark:text-white'>SycoLibre</h1>
						<div className='flex items-center space-x-4'>
							<NotificationBell />
							<SearchUsers />
							<FriendsList friends={friends} />
							<DarkModeToggle />
							<UserProfileMenu />
						</div>
					</div>
				</div>
			</header>

			{/* Main Content */}
			<main className='max-w-7xl mx-auto py-6 sm:px-6 lg:px-8'>
				<Outlet />
			</main>
		</div>
	);
};

const AuthenticatedLayout: React.FC = () => (
	<FriendsProvider>
		<AuthenticatedLayoutInner />
	</FriendsProvider>
);

export default AuthenticatedLayout;
