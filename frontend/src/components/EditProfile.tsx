import React, { FormEvent, useEffect, useState } from 'react';
import { profileEditAPI } from '../services/profileEditAPI';
import { User } from '../types/userType';

interface UserEditProps {
	token: string;
}

const EditProfile: React.FC<UserEditProps> = ({ token }) => {
	const [email, setEmail] = useState<string>('');
	const [display_name, setDisplayName] = useState<string>('');
	const [profile_picture_url, setProfilePictureUrl] = useState<string>('');
	const [loading, setLoading] = useState<boolean>(true);

	useEffect(() => {
		profileEditAPI
			.getProfile(token)
			.then((user: User) => {
				setEmail(user.email ?? '');
				setDisplayName(user.username ?? '');
				setProfilePictureUrl(user.profile_picture ?? '');
				setLoading(false);
			})
			.catch((err: unknown) => {
				console.error('Failed to load user data', err);
				setLoading(false);
			});
	}, [token]);

	const handleSubmit = async (e: FormEvent) => {
		e.preventDefault();

		try {
			await profileEditAPI.updateProfile(
				{ email, display_name, profile_picture: profile_picture_url },
				token
			);
			alert('User updated!');
		} catch (err) {
			console.error('Failed to update user', err);
			alert('Failed to update user');
		}
	};

	if (loading) return <p>Loading user data...</p>;

	return (
		<form onSubmit={handleSubmit} className='flex flex-col gap-4'>
			<div className='flex flex-col gap-1'>
				<label htmlFor='email' className='text-sm font-medium text-gray-700 dark:text-gray-200'>
					Email
				</label>
				<input
					id='email'
					type='email'
					value={email}
					onChange={(e) => setEmail(e.target.value)}
					required
					className='rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
				/>
			</div>
			<div className='flex flex-col gap-1'>
				<label
					htmlFor='display_name'
					className='text-sm font-medium text-gray-700 dark:text-gray-200'
				>
					Display Name
				</label>
				<input
					id='display_name'
					type='text'
					value={display_name}
					onChange={(e) => setDisplayName(e.target.value)}
					className='rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
				/>
			</div>
			<div className='flex flex-col gap-1'>
				<label
					htmlFor='profile_picture_url'
					className='text-sm font-medium text-gray-700 dark:text-gray-200'
				>
					Profile Picture URL
				</label>
				<input
					id='profile_picture_url'
					type='text'
					value={profile_picture_url}
					onChange={(e) => setProfilePictureUrl(e.target.value)}
					className='rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
				/>
			</div>
			<button
				type='submit'
				className='mt-2 bg-primary-600 hover:bg-primary-700 text-white font-semibold py-2 px-4 rounded-md shadow focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2'
			>
				Update Profile
			</button>
		</form>
	);
};

export default EditProfile;
