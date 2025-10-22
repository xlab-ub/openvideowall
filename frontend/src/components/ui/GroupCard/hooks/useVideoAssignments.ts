// frontend/src/components/ui/GroupCard/hooks/useVideoAssignments.ts

import { useState, useEffect } from 'react';
import { VideoAssignment } from '../types';

// Helper function to get storage key for a group's video assignments
const getStorageKey = (groupId: string) => `video_assignments_${groupId}`;

// Helper function to save video assignments and selected video to localStorage
const saveVideoAssignments = (groupId: string, assignments: VideoAssignment[], selectedVideo?: string) => {
  try {
    const key = getStorageKey(groupId);
    const data = {
      assignments,
      selectedVideo: selectedVideo || '',
      timestamp: Date.now(),
      version: '1.0'
    };
    localStorage.setItem(key, JSON.stringify(data));
    console.log(` Saved video assignments for group ${groupId}:`, assignments, 'selectedVideo:', selectedVideo);
  } catch (error) {
    console.warn(' Failed to save video assignments to localStorage:', error);
  }
};

// Helper function to load video assignments and selected video from localStorage
const loadVideoAssignments = (groupId: string, screenCount: number): { assignments: VideoAssignment[], selectedVideo: string } => {
  try {
    const key = getStorageKey(groupId);
    const stored = localStorage.getItem(key);

    if (stored) {
      const data = JSON.parse(stored);
      const assignments = data.assignments || [];
      const selectedVideo = data.selectedVideo || '';

      // Validate that we have the right number of screens and structure
      if (Array.isArray(assignments) && assignments.length === screenCount) {
        // Validate each assignment has the correct structure
        const validAssignments = assignments.every((assignment, index) =>
          assignment &&
          typeof assignment === 'object' &&
          assignment.screen === index &&
          typeof assignment.file === 'string'
        );

        if (validAssignments) {
          console.log(` Loaded video assignments for group ${groupId}:`, assignments, 'selectedVideo:', selectedVideo);
          return { assignments, selectedVideo };
        }
      }
    }
  } catch (error) {
    console.warn(' Failed to load video assignments from localStorage:', error);
  }

  // Return empty assignments if loading failed or data is invalid
  return {
    assignments: Array.from({ length: screenCount }, (_, index) => ({
      screen: index,
      file: ""
    })),
    selectedVideo: ''
  };
};

export const useVideoAssignments = (groupId: string, screenCount: number, onVideoChange?: () => void, enableAutoRestart: boolean = true) => {
  const [videoAssignments, setVideoAssignments] = useState<VideoAssignment[]>([]);
  const [showVideoConfig, setShowVideoConfig] = useState(false);
  const [selectedVideoFile, setSelectedVideoFile] = useState<string>('');
  const [isSaving, setIsSaving] = useState(false);

  // Load saved video assignments and selected video when group changes or component mounts
  useEffect(() => {
    const savedData = loadVideoAssignments(groupId, screenCount);
    setVideoAssignments(savedData.assignments);
    setSelectedVideoFile(savedData.selectedVideo);

    // Auto-expand video config if assignments exist
    const hasAssignments = savedData.assignments.some(assignment => assignment.file);
    setShowVideoConfig(hasAssignments);
  }, [groupId, screenCount]);

  // Handle video assignment change and save to localStorage
  const handleVideoAssignmentChange = (screenIndex: number, fileName: string) => {
    // Convert special clear value to empty string
    const actualFileName = fileName === "__CLEAR__" ? "" : fileName;

    const newAssignments = videoAssignments.map((assignment, index) =>
      index === screenIndex ? { ...assignment, file: actualFileName } : assignment
    );

    setVideoAssignments(newAssignments);

    // Save to localStorage immediately when user makes changes
    saveVideoAssignments(groupId, newAssignments, selectedVideoFile);

    // Trigger restart if callback provided and auto-restart is enabled
    if (onVideoChange && enableAutoRestart) {
      // Use a small delay to ensure state is updated
      setTimeout(() => {
        restartWithCurrentState();
      }, 100);
    }
  };

  // Reset video assignments to empty
  const resetVideoAssignments = () => {
    const emptyAssignments: VideoAssignment[] = Array.from({ length: screenCount }, (_, index) => ({
      screen: index,
      file: ""
    }));
    setVideoAssignments(emptyAssignments);
    setSelectedVideoFile(''); // Also reset selected video
    saveVideoAssignments(groupId, emptyAssignments, '');
  };

  // Wrapper for setSelectedVideoFile that also saves to localStorage
  const setSelectedVideoFileAndSave = (fileName: string) => {
    setSelectedVideoFile(fileName);
    saveVideoAssignments(groupId, videoAssignments, fileName);
    
    // Trigger restart if callback provided and auto-restart is enabled
    if (onVideoChange && enableAutoRestart) {
      // Use a small delay to ensure state is updated
      setTimeout(() => {
        restartWithCurrentState();
      }, 100);
    }
  };

  // Manual save function that always triggers restart
  const saveVideoChanges = async () => {
    if (onVideoChange) {
      setIsSaving(true);
      try {
        console.log(` Manual save triggered for group ${groupId}`);
        await restartWithCurrentState();
        
        // Keep popup open for a moment to show success
        console.log(` ✅ Video changes saved and streaming restarted`);
        
        // Optional: Add a small delay to show success message
        await new Promise(resolve => setTimeout(resolve, 1000));
        
      } finally {
        setIsSaving(false);
      }
    }
  };

  // Enhanced restart function that uses current state
  const restartWithCurrentState = async () => {
    if (!onVideoChange) return;
    
    try {
      console.log(` Restarting streaming with current video assignments for group ${groupId}`);
      
      // Import API here to avoid circular dependency
      const { api } = await import('../../../../API/api');
      
      // Stop current streaming
      await api.group.stopGroup(groupId);
      console.log(` Current streaming stopped, restarting...`);
      
      // Wait a moment for cleanup
      await new Promise(resolve => setTimeout(resolve, 2000)); // Increased wait time
      
      // Get group info to determine streaming mode
      const groupsResponse = await api.group.getGroups();
      const currentGroup = groupsResponse.groups.find((g: any) => g.id === groupId);
      
      if (!currentGroup) {
        console.error(` Group ${groupId} not found`);
        return;
      }
      
      console.log(` Group streaming mode: ${currentGroup.streaming_mode}`);
      
      // Restart based on group's streaming mode
      if (currentGroup.streaming_mode === 'single_video_split') {
        if (!selectedVideoFile) {
          console.log(` No video file selected for split mode`);
          return;
        }
        console.log(` Starting single video split with: ${selectedVideoFile}`);
        await api.group.startSingleVideoSplit(groupId, {
          video_file: selectedVideoFile,
          screen_count: currentGroup.screen_count,
          orientation: currentGroup.orientation,
          enable_looping: true
        });
      } else {
        // Multi-video mode
        const validAssignments = videoAssignments.filter(assignment => assignment.file);
        if (validAssignments.length === 0) {
          console.log(` No video assignments for multi-video mode`);
          return;
        }
        console.log(` Starting multi-video with ${validAssignments.length} assignments`);
        await api.group.startMultiVideoGroup(groupId, validAssignments, {
          screen_count: currentGroup.screen_count,
          orientation: currentGroup.orientation
        });
      }
      
      console.log(` ✅ Streaming restarted successfully for group ${groupId}`);
      
      // Verify streaming is actually working by checking group status
      await verifyStreamingStatus(groupId);
      
    } catch (error) {
      console.error(` ❌ Error restarting streaming for group ${groupId}:`, error);
      // Show error to user
      alert(`Failed to restart streaming: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  // Verify streaming status after restart
  const verifyStreamingStatus = async (groupId: string) => {
    try {
      console.log(` 🔍 Verifying streaming status for group ${groupId}...`);
      
      // Wait a moment for streaming to initialize
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Check group status
      const { api } = await import('../../../../API/api');
      const groupsResponse = await api.group.getGroups();
      const group = groupsResponse.groups.find((g: any) => g.id === groupId);
      
      if (group && group.is_streaming) {
        console.log(` ✅ Streaming verification successful for group ${groupId}`);
        return true;
      } else {
        console.warn(` ⚠️ Streaming verification failed for group ${groupId} - not streaming`);
        return false;
      }
    } catch (error) {
      console.error(` ❌ Error verifying streaming status for group ${groupId}:`, error);
      return false;
    }
  };

  // Check if all screens have video assignments
  const hasCompleteAssignments = videoAssignments.every(assignment => assignment.file);

  // Check if any assignments exist
  const hasAnyAssignments = videoAssignments.some(assignment => assignment.file);

  return {
    videoAssignments,
    showVideoConfig,
    setShowVideoConfig,
    selectedVideoFile,
    setSelectedVideoFile: setSelectedVideoFileAndSave, // Use the wrapper that saves to localStorage
    handleVideoAssignmentChange,
    resetVideoAssignments,
    hasCompleteAssignments,
    hasAnyAssignments,
    saveVideoChanges, // Manual save function
    isSaving // Loading state for save button
  };
};