"""GraphQL query strings for the Octopus Kraken Italia API.

All queries are extracted verbatim from Proxyman network captures
of the official Octopus Energy Italia mobile app.
"""

from __future__ import annotations

# --- Authentication ---

LOGIN = """
mutation Login($input: ObtainJSONWebTokenInput!) {
  obtainKrakenToken(input: $input) {
    __typename
    refreshExpiresIn
    refreshToken
    token
  }
}
"""

# --- Account ---

GET_ACCOUNT_LIST = """
query GetAccountList {
  viewer {
    __typename
    accounts {
      __typename
      number
    }
  }
}
"""

GET_ACCOUNT_PROPERTIES = """
query GetAccountProperties($accountNumber: String!) {
  account(accountNumber: $accountNumber) {
    __typename
    properties {
      __typename
      id
      address
      splitAddress
      postcode
      occupancyPeriods {
        __typename
        effectiveTo
        effectiveFrom
      }
    }
    number
  }
}
"""

# --- SmartFlex Devices ---

GET_SMART_FLEX_DEVICES = """
query GetSmartFlexDevices($accountNumber: String!, $deviceId: String) {
  devices(accountNumber: $accountNumber, deviceId: $deviceId) {
    __typename
    id
    name
    deviceType
    provider
    propertyId
    integrationDeviceId
    status {
      __typename
      current
      isSuspended
    }
    preferences {
      __typename
      gridExport
    }
    ... on SmartFlexVehicle {
      make
    }
  }
}
"""

GET_SMART_FLEX_DEVICE_PREFERENCES = """
query GetSmartFlexDevicePreferences($accountNumber: String!, $deviceId: String) {
  devices(accountNumber: $accountNumber, deviceId: $deviceId) {
    __typename
    id
    preferences {
      __typename
      targetType
      unit
      mode
      gridExport
      schedules {
        __typename
        dayOfWeek
        time
        min
        max
        upperLimit
      }
      isChargingDurationCapped
    }
  }
}
"""

SET_SMART_FLEX_DEVICE_PREFERENCES = """
mutation SetSmartFlexDevicePreferences($input: SmartFlexDevicePreferencesInput!) {
  setDevicePreferences(input: $input) {
    __typename
    id
    preferences {
      __typename
      targetType
      unit
      mode
      schedules {
        __typename
        dayOfWeek
        time
        min
        max
      }
    }
  }
}
"""

GET_SMART_FLEX_DEVICE_PREFERENCE_SETTINGS = """
query GetSmartFlexDevicePreferenceSettings($accountNumber: String!, $deviceId: String) {
  devices(accountNumber: $accountNumber, deviceId: $deviceId) {
    __typename
    id
    propertyId
    deviceType
    provider
    preferenceSetting {
      __typename
      mode
      unit
      scheduleSettings {
        __typename
        timeFrom
        timeTo
        timeStep
        min
        minConstraint {
          __typename
          min
          max
        }
        max
        step
      }
    }
  }
}
"""

GET_SMART_FLEX_DEVICE_ALERTS = """
query GetSmartFlexDeviceAlerts($accountNumber: String!) {
  devices(accountNumber: $accountNumber) {
    __typename
    id
    alerts {
      __typename
      message
      publishedAt
    }
  }
}
"""

GET_SMART_FLEX_PLANNED_DISPATCHES = """
query GetSmartFlexPlannedDispatches($accountNumber: String!) {
  plannedDispatches(accountNumber: $accountNumber) {
    start
    end
    delta
    meta {
      source
      location
    }
  }
}
"""
