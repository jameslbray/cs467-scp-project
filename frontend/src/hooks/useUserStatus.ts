import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../contexts/auth/authContext";
import { StatusAPI } from "../services/statusAPI";
import { StatusType } from "../types";

export const useUserStatus = () => {
	const [status, setStatus] = useState<StatusType>(StatusType.OFFLINE);
	const [isLoading, setIsLoading] = useState<boolean>(false);
	const [error, setError] = useState<string | null>(null);

	const { user, token } = useAuth();

	const loadStatus = useCallback(async () => {
		if (!user) {
			setError("User is not logged in");
			return;
		}

		setIsLoading(true);
		try {
			if (!token) {
				setError("Authentication token is missing");
				setIsLoading(false);
				return;
			}
			const result = await StatusAPI.getUserStatus(user.id, token);
			if (result) {
				setStatus(result.status as StatusType);
			}
			setError(null);
		} catch (err) {
			setError(err instanceof Error ? err.message : "Unknown error occurred");
		} finally {
			setIsLoading(false);
		}
	}, [user, token]);

	const updateStatus = async (newStatus: StatusType) => {
		if (!user) {
			setError("User is not logged in");
			return;
		}

		setIsLoading(true);

		try {
			if (!token) {
				setError("Authentication token is missing");
				setIsLoading(false);
				return;
			}
			const result = await StatusAPI.updateUserStatus(
				user.id,
				{ status: newStatus, additional_info: null },
				token,
			);

			if (result) {
				setStatus(result.status as StatusType);
				setError(null);
			} else {
				setError("Failed to update status");
			}
		} catch (err) {
			setError(err instanceof Error ? err.message : "Unknown error occurred");
		} finally {
			setIsLoading(false);
		}
	};

	useEffect(() => {
		if (user && token) {
			loadStatus();
		}
	}, [user, token, loadStatus]);

	return {
		status,
		isLoading,
		error,
		updateStatus,
	};
};
