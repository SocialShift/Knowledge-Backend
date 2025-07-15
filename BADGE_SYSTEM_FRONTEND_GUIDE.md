# 🏆 Badge System Frontend Implementation Guide

## Overview
This guide explains how to implement the badge system on the frontend. The backend stores badges as JSON in the user's profile and returns badge updates in real-time when users earn new badges.

## 📊 Badge Data Structure

### User Profile Badge Format
When you fetch a user's profile (`/api/auth/user/me`), badges are returned in this format:

```json
{
  "profile": {
    "badges": [
      {
        "id": "spark",
        "name": "Spark",
        "path": "illumination",
        "tier": "1",
        "description": "You've taken the first step into untold truths",
        "icon_url": "media/badges/spark.png",
        "earned_at": "2024-01-15T10:30:00.000Z"
      },
      {
        "id": "truth_seeker",
        "name": "Truth Seeker",
        "path": "starter",
        "tier": "0",
        "description": "Welcome to Knowledge. Your journey to uncover hidden truths begins now.",
        "icon_url": "media/badges/truth_seeker.png",
        "earned_at": "2024-01-10T08:00:00.000Z"
      }
    ]
  }
}
```

### Badge Update Format
When users earn new badges, APIs return real-time updates:

```json
{
  "badge_updates": {
    "newly_earned_badges": [
      {
        "id": "candlebearer",
        "name": "Candlebearer",
        "path": "illumination",
        "tier": "2",
        "description": "You're starting to light the darkness with knowledge",
        "icon_url": "media/badges/candlebearer.png",
        "earned_at": "2024-01-20T14:45:00.000Z"
      }
    ],
    "current_badges": [...], // All user's badges
    "progress": {
      "stories_completed": 12,
      "timelines_completed": 1,
      "games_played": 5,
      "streak_days": 7
    },
    "unlock_messages": [
      "🎉 Badge Unlocked: Candlebearer\nYou're starting to light the darkness with knowledge."
    ]
  }
}
```

## 🎯 All Available Badges

### 🔦 Illumination Path (Story & Timeline Completion)
| Badge | ID | Tier | Criteria | Description |
|-------|----|----|----------|-------------|
| Spark | `spark` | 1 | 3 stories | You've taken the first step into untold truths |
| Candlebearer | `candlebearer` | 2 | 10 stories | You're starting to light the darkness with knowledge |
| Torchbearer | `torchbearer` | 3 | 25 stories | You carry the truth forward, one story at a time |
| Flamekeeper | `flamekeeper` | 4 | 50 stories + 2 timelines | You protect what others tried to extinguish |
| Beacon | `beacon` | 5 | 100 stories + 5 timelines | You shine so others can see. Your knowledge guides generations |
| Constellation | `constellation` | 6 | 3+ identity categories | You've connected erased histories across communities |

### 🎮 Game Path
| Badge | ID | Tier | Criteria | Description |
|-------|----|----|----------|-------------|
| Uncover | `uncover` | 1 | Play 1 game | Play 1 game of any type |
| Seeker | `seeker` | 2 | 3 game types | Play 3 different game types |
| Revealer | `revealer` | 3 | 3 high scores | Score 80%+ on 3 games |
| Historian | `historian` | 4 | 10 games | Play 10 total games |
| Archivist | `archivist` | 5 | 1 challenge set | Complete all games in a challenge set |

### 🔥 Streak Path (Login Consistency)
| Badge | ID | Tier | Criteria | Description |
|-------|----|----|----------|-------------|
| Ember | `ember` | 1 | 3-day streak | 3-day streak |
| Flame | `flame` | 2 | 7-day streak | 7-day streak |
| Inferno | `inferno` | 3 | 30-day streak | 30-day streak |
| Eternal Flame | `eternal_flame` | 4 | 90-day streak | 90-day streak |

### 🌟 Starter Badges (Default for Everyone)
| Badge | ID | Tier | Criteria | Description |
|-------|----|----|----------|-------------|
| Truth Seeker | `truth_seeker` | 0 | Default | Welcome to Knowledge. Your journey to uncover hidden truths begins now. |
| First Step | `first_step` | 0 | Default | Every journey begins with a single step. You've taken yours. |

## 🚀 API Endpoints That Return Badge Updates

### When Badge Updates Are Sent
Badge updates are included in API responses when users earn new badges:

1. **Story Viewing**: `GET /api/story/{story_id}` - When viewing a story for the first time
2. **Quiz Completion**: `POST /api/quiz/submit` - When completing a quiz
3. **Game Completion**: `POST /api/game/attempt` - When playing a game
4. **Timeline Viewing**: `GET /api/timeline/{timeline_id}` - When viewing a timeline for the first time
5. **Profile Access**: `GET /api/auth/user/me` - When login streak badges are earned

### Example API Response with Badge Update
```json
{
  "story": {
    "id": 123,
    "title": "Story Title",
    // ... other story data
  },
  "badge_updates": {
    "newly_earned_badges": [
      {
        "id": "spark",
        "name": "Spark",
        "path": "illumination",
        "tier": "1",
        "description": "You've taken the first step into untold truths",
        "icon_url": "media/badges/spark.png",
        "earned_at": "2024-01-20T14:45:00.000Z"
      }
    ],
    "unlock_messages": [
      "🎉 Badge Unlocked: Spark\nYou've taken the first step into untold truths — keep going."
    ]
  }
}
```

## 🎨 UI Implementation Recommendations

### 1. Badge Display Components

#### Badge Icon Component
```jsx
const BadgeIcon = ({ badge, size = 'medium' }) => {
  const sizeClasses = {
    small: 'w-8 h-8',
    medium: 'w-12 h-12',
    large: 'w-16 h-16'
  };

  return (
    <div className={`${sizeClasses[size]} relative`}>
      <img 
        src={badge.icon_url} 
        alt={badge.name}
        className="w-full h-full object-cover rounded-full"
      />
      {/* Tier indicator */}
      <span className="absolute -top-1 -right-1 bg-blue-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
        {badge.tier}
      </span>
    </div>
  );
};
```

#### Badge Grid Component
```jsx
const BadgeGrid = ({ badges }) => {
  const groupedBadges = badges.reduce((acc, badge) => {
    if (!acc[badge.path]) acc[badge.path] = [];
    acc[badge.path].push(badge);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      {Object.entries(groupedBadges).map(([path, pathBadges]) => (
        <div key={path}>
          <h3 className="text-lg font-semibold mb-3 capitalize">
            {path} Path
          </h3>
          <div className="grid grid-cols-3 md:grid-cols-5 gap-4">
            {pathBadges.map(badge => (
              <div key={badge.id} className="text-center">
                <BadgeIcon badge={badge} />
                <p className="text-sm mt-2">{badge.name}</p>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};
```

### 2. Badge Unlock Modal
```jsx
const BadgeUnlockModal = ({ badge, isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 max-w-md mx-4 text-center">
        <div className="mb-4">
          <BadgeIcon badge={badge} size="large" />
        </div>
        <h2 className="text-xl font-bold mb-2">Badge Unlocked!</h2>
        <h3 className="text-lg text-blue-600 mb-2">{badge.name}</h3>
        <p className="text-gray-600 mb-4">{badge.description}</p>
        <button 
          onClick={onClose}
          className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
        >
          Continue
        </button>
      </div>
    </div>
  );
};
```

### 3. Badge Progress Indicator
```jsx
const BadgeProgress = ({ currentProgress, nextBadge }) => {
  if (!nextBadge) return null;

  const criteria = nextBadge.criteria;
  const progressPercentage = Math.min(
    (currentProgress.stories_completed / criteria.stories_completed) * 100,
    100
  );

  return (
    <div className="bg-gray-100 rounded-lg p-4">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium">Next Badge: {nextBadge.name}</span>
        <span className="text-sm text-gray-500">
          {currentProgress.stories_completed}/{criteria.stories_completed}
        </span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2">
        <div 
          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
          style={{ width: `${progressPercentage}%` }}
        />
      </div>
    </div>
  );
};
```

## 🔄 Implementation Flow

### 1. Handle Badge Updates in API Calls
```javascript
// Example: Story viewing
const viewStory = async (storyId) => {
  try {
    const response = await fetch(`/api/story/${storyId}`);
    const data = await response.json();
    
    // Handle badge updates if present
    if (data.badge_updates && data.badge_updates.newly_earned_badges.length > 0) {
      // Show badge unlock modal
      showBadgeUnlockModal(data.badge_updates.newly_earned_badges[0]);
      
      // Update user's badge collection in state
      updateUserBadges(data.badge_updates.current_badges);
    }
    
    return data;
  } catch (error) {
    console.error('Error viewing story:', error);
  }
};
```

### 2. State Management
```javascript
// Redux/Context state structure
const initialState = {
  user: {
    profile: {
      badges: [],
      // ... other profile data
    }
  },
  badgeModal: {
    isOpen: false,
    badge: null
  }
};

// Actions
const updateUserBadges = (badges) => ({
  type: 'UPDATE_USER_BADGES',
  payload: badges
});

const showBadgeModal = (badge) => ({
  type: 'SHOW_BADGE_MODAL',
  payload: badge
});
```

### 3. Badge Notification System
```javascript
// Show badge unlock notification
const showBadgeUnlockModal = (badge) => {
  // Play sound effect
  playBadgeUnlockSound();
  
  // Show modal with animation
  setBadgeModal({
    isOpen: true,
    badge: badge
  });
  
  // Optional: Show toast notification
  toast.success(`🎉 Badge Unlocked: ${badge.name}!`);
};
```

## 🎯 Key Implementation Points

### 1. **Real-time Updates**
- Check for `badge_updates` in API responses
- Show unlock modals immediately when badges are earned
- Update the user's badge collection in your state management

### 2. **Badge Retention**
- Some badges can be lost if users don't maintain activity (7-day retention rule)
- Update badge display when the user profile is refreshed

### 3. **Progress Tracking**
- Use the `progress` object in badge updates to show progress toward next badges
- Display progress bars for badge paths

### 4. **Badge Paths**
- Group badges by their `path` property for better organization
- Show progression within each path (tier 1 → 2 → 3, etc.)

### 5. **Default Badges**
- All users start with "Truth Seeker" and "First Step" badges
- These are tier 0 and should be displayed differently

## 🎨 Design Recommendations

### Badge Colors by Path
- **Illumination**: Gold/Yellow theme (🔦)
- **Game**: Green theme (🎮)
- **Streak**: Red/Orange theme (🔥)
- **Starter**: Blue theme (🌟)

### Badge States
- **Earned**: Full color, clickable for details
- **Locked**: Grayscale with lock icon
- **Progress**: Semi-transparent with progress indicator

### Animations
- **Unlock**: Scale up with glow effect
- **Progress**: Smooth progress bar animations
- **Hover**: Subtle scale and shadow effects

This should give your frontend developer everything they need to implement a comprehensive badge system! Let me know if you need any clarification or additional examples. 