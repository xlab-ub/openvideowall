// Alternative: Self-loading ClientsTab - frontend/src/components/ClientsTab.tsx

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { ArrowUp, ArrowDown, Monitor, Wifi, WifiOff, Search, Users, RefreshCw } from "lucide-react";
import { useErrorHandler } from "@/components/ErrorSystem/useErrorHandler";
import { clientApi } from '@/API/api';
import type { Client } from '@/types';

// Make ClientsTab self-loading (remove props dependency)
const ClientsTab = () => {
  const { showError } = useErrorHandler();
  const [searchTerm, setSearchTerm] = useState('');
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  // Load clients data
  const loadClients = async (showRefreshing = false) => {
    try {
      if (showRefreshing) setRefreshing(true);
      setLoading(true);
      console.log(' Loading clients data...');

      const clientsData = await clientApi.getClients();
      console.log(' Raw API response:', clientsData);
      console.log(' All clients:', clientsData.clients);

      // Show ALL clients (both active and offline)
      const allClients = clientsData.clients || [];
      console.log(' All clients (active and offline):', allClients);

      setClients(allClients);

      if (showRefreshing) {
        showError({
          message: `Clients refreshed successfully. Found ${allClients.length} clients (${allClients.filter(c => c.status === 'active').length} active, ${allClients.filter(c => c.status === 'inactive').length} offline)`,
          error_code: 'CLIENTS_REFRESHED',
          error_category: '2xx',
          context: {
            component: 'ClientsTab',
            operation: 'refreshClients',
            total_clients: allClients.length,
            active_clients: allClients.filter(c => c.status === 'active').length,
            offline_clients: allClients.filter(c => c.status === 'inactive').length,
            timestamp: new Date().toISOString()
          }
        });
      }
    } catch (error: any) {
      console.error(' Error loading clients:', error);
      showError({
        message: "Failed to load clients",
        error_code: 'CLIENTS_LOAD_FAILED',
        error_category: '5xx',
        context: {
          component: 'ClientsTab',
          operation: 'loadClients',
          timestamp: new Date().toISOString(),
          original_error: error?.message,
          stack: error?.stack
        }
      });
    } finally {
      setLoading(false);
      if (showRefreshing) setRefreshing(false);
    }
  };

  // Load initial data and set up refresh interval
  useEffect(() => {
    loadClients();

    // Refresh clients every 5 seconds
    const interval = setInterval(() => {
      loadClients();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const moveClient = (clientId: string, direction: 'up' | 'down') => {
    const clientIndex = clients.findIndex(c => c.client_id === clientId);
    if (
      (direction === 'up' && clientIndex === 0) ||
      (direction === 'down' && clientIndex === clients.length - 1)
    ) {
      return;
    }

    const newClients = [...clients];
    const targetIndex = direction === 'up' ? clientIndex - 1 : clientIndex + 1;

    [newClients[clientIndex], newClients[targetIndex]] = [newClients[targetIndex], newClients[clientIndex]];
    setClients(newClients);
  };

  const unassignClient = async (clientId: string) => {
    try {
      console.log(`Unassigning client ${clientId}`);
      
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/clients/unassign_client`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_id: clientId,
          unassign_type: 'all'  // Unassign from everything
        }),
      });

      if (response.ok) {
        const result = await response.json();
        console.log('Unassign successful:', result);
        
        showError({
          message: `Client ${clientId} unassigned successfully`,
          error_code: 'CLIENT_UNASSIGNED',
          error_category: '2xx',
          context: {
            component: 'ClientsTab',
            operation: 'unassignClient',
            client_id: clientId,
            timestamp: new Date().toISOString()
          }
        });
        
        // Refresh the client list
        loadClients();
      } else {
        const error = await response.json();
        throw new Error(error.error || 'Failed to unassign client');
      }
    } catch (error: any) {
      console.error('Error unassigning client:', error);
      showError({
        message: `Failed to unassign client: ${error.message}`,
        error_code: 'CLIENT_UNASSIGN_FAILED',
        error_category: '5xx',
        context: {
          component: 'ClientsTab',
          operation: 'unassignClient',
          client_id: clientId,
          timestamp: new Date().toISOString(),
          original_error: error?.message
        }
      });
    }
  };

  const removeClient = async (clientId: string) => {
    if (!confirm(`Are you sure you want to remove client ${clientId}? This will permanently delete the client from the system.`)) {
      return;
    }

    try {
      console.log(`Removing client ${clientId}`);
      
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'}/api/clients/remove_client`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          client_id: clientId
        }),
      });

      if (response.ok) {
        const result = await response.json();
        console.log('Remove successful:', result);
        
        showError({
          message: `Client ${clientId} removed successfully`,
          error_code: 'CLIENT_REMOVED',
          error_category: '2xx',
          context: {
            component: 'ClientsTab',
            operation: 'removeClient',
            client_id: clientId,
            timestamp: new Date().toISOString()
          }
        });
        
        // Refresh the client list
        loadClients();
      } else {
        const error = await response.json();
        throw new Error(error.error || 'Failed to remove client');
      }
    } catch (error: any) {
      console.error('Error removing client:', error);
      showError({
        message: `Failed to remove client: ${error.message}`,
        error_code: 'CLIENT_REMOVE_FAILED',
        error_category: '5xx',
        context: {
          component: 'ClientsTab',
          operation: 'removeClient',
          client_id: clientId,
          timestamp: new Date().toISOString(),
          original_error: error?.message
        }
      });
    }
  };

  const filteredClients = clients.filter(client => {
    if (!searchTerm) return true;

    const searchLower = searchTerm.toLowerCase();
    return (
      (client.display_name?.toLowerCase().includes(searchLower)) ||
      (client.hostname?.toLowerCase().includes(searchLower)) ||
      (client.client_id?.toLowerCase().includes(searchLower)) ||
      (client.ip_address?.toLowerCase().includes(searchLower))
    );
  });

  // Debug logging
  useEffect(() => {
    console.log(' ClientsTab state:', {
      loading,
      clientsCount: clients.length,
      filteredCount: filteredClients.length,
      clients: clients
    });
  }, [loading, clients, filteredClients]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">Loading clients...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Card className="bg-white border border-gray-200">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Users className="w-5 h-5" />
                All Clients ({clients.length})
              </CardTitle>
              <CardDescription>
                All clients (online and offline). Shows comprehensive details including assignments, stream URLs, and timestamps. Auto-refreshes every 5 seconds.
              </CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => loadClients(true)}
              disabled={refreshing}
              className="flex items-center gap-2"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </CardHeader>

        <CardContent>
          {/* Search */}
          <div className="mb-6">
            <div className="relative">
              <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search clients by name, hostname, ID, or IP..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>

          {/* Debug Info */}
          <div className="mb-4 p-3 bg-gray-100 rounded text-sm text-gray-600">
            Debug: {clients.length} total clients ({clients.filter(c => c.status === 'active').length} online, {clients.filter(c => c.status === 'inactive' && c.assignment_status === 'screen_assigned' && c.stream_url).length} streaming without heartbeat, {clients.filter(c => c.status === 'inactive' && !(c.assignment_status === 'screen_assigned' && c.stream_url)).length} offline), {filteredClients.length} shown after filtering
            {clients.filter(c => c.status === 'inactive' && c.assignment_status === 'screen_assigned' && c.stream_url).length > 0 && (
              <div className="mt-2 text-yellow-700">
                ⚠️ Some clients are streaming but not sending heartbeats. They may be running old client code.
              </div>
            )}
          </div>

          {/* Clients List */}
          <div className="space-y-3">
            {filteredClients.length === 0 ? (
              <div className="text-center py-8">
                <Monitor className="w-12 h-12 text-gray-300 mx-auto mb-3" />
                <h3 className="text-lg font-medium text-gray-700 mb-2">
                  {clients.length === 0 ? 'No Clients' : 'No Clients Found'}
                </h3>
                <p className="text-gray-500">
                  {searchTerm
                    ? 'No clients match your search criteria.'
                    : clients.length === 0
                      ? 'No clients have been registered with the server. When clients connect, they will appear here automatically.'
                      : 'All clients are filtered out.'
                  }
                </p>
                {clients.length === 0 && (
                  <Button
                    variant="outline"
                    onClick={() => loadClients(true)}
                    className="mt-4"
                  >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Check for Clients
                  </Button>
                )}
              </div>
            ) : (
              filteredClients.map((client, index) => (
                <div
                  key={client.client_id || `client-${index}`}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200 hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center gap-4">
                    {/* Show status indicator */}
                    <div className={`w-3 h-3 rounded-full ${
                      client.status === 'active' 
                        ? 'bg-green-500' 
                        : client.assignment_status === 'screen_assigned' && client.stream_url
                          ? 'bg-yellow-500'
                          : 'bg-red-500'
                    }`} />

                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-medium text-gray-900">
                          {client.display_name || client.hostname || client.client_id}
                        </h3>
                        {/* Show status based on heartbeat and assignments */}
                        <Badge 
                          variant="default" 
                          className={client.status === 'active' 
                            ? 'bg-green-100 text-green-800 border-green-200' 
                            : client.assignment_status === 'screen_assigned' && client.stream_url
                              ? 'bg-yellow-100 text-yellow-800 border-yellow-200'
                              : 'bg-red-100 text-red-800 border-red-200'
                          }
                        >
                          {client.status === 'active' 
                            ? 'Online' 
                            : client.assignment_status === 'screen_assigned' && client.stream_url
                              ? 'Streaming (No Heartbeat)'
                              : 'Offline'
                          }
                        </Badge>
                      </div>

                      <div className="space-y-2">
                        {/* Basic Info Row */}
                        <div className="flex items-center gap-4 text-sm text-gray-600">
                          <span><strong>IP:</strong> {client.ip_address}</span>
                          <span><strong>ID:</strong> {client.client_id}</span>
                          <span><strong>Hostname:</strong> {client.hostname}</span>
                        </div>
                        
                        {/* Assignment Info Row */}
                        <div className="flex items-center gap-2 flex-wrap">
                          {client.group_name && (
                            <Badge variant="secondary" className="text-xs">
                              <strong>Group:</strong> {client.group_name}
                            </Badge>
                          )}
                          {client.assignment_status && (
                            <Badge 
                              variant={client.assignment_status === 'screen_assigned' ? 'default' : 'outline'} 
                              className="text-xs"
                            >
                              <strong>Status:</strong> {client.assignment_status}
                            </Badge>
                          )}
                          {client.screen_number !== undefined && client.screen_number !== null && (
                            <Badge variant="outline" className="text-xs">
                              <strong>Screen:</strong> {client.screen_number + 1}
                            </Badge>
                          )}
                          {client.stream_assignment && (
                            <Badge variant="outline" className="text-xs">
                              <strong>Stream:</strong> {client.stream_assignment}
                            </Badge>
                          )}
                        </div>
                        
                        {/* Stream URL and Technical Details */}
                        <div className="space-y-1">
                          {client.stream_url && (
                            <div className="text-xs text-gray-500">
                              <strong>Stream URL:</strong> 
                              <div className="font-mono bg-gray-100 p-1 rounded mt-1 break-all">
                                {client.stream_url}
                              </div>
                            </div>
                          )}
                          
                          {/* Technical Details */}
                          <div className="flex items-center gap-4 text-xs text-gray-500">
                            {client.platform && (
                              <span><strong>Platform:</strong> {client.platform}</span>
                            )}
                            {client.srt_ip && (
                              <span><strong>SRT IP:</strong> {client.srt_ip}</span>
                            )}
                            {client.stream_version && (
                              <span><strong>Stream Version:</strong> {client.stream_version}</span>
                            )}
                          </div>
                          
                          {/* Timestamps */}
                          <div className="flex items-center gap-4 text-xs text-gray-500">
                            {client.registered_at && (
                              <span><strong>Registered:</strong> {new Date(client.registered_at * 1000).toLocaleString()}</span>
                            )}
                            {client.assigned_at && (
                              <span><strong>Assigned:</strong> {new Date(client.assigned_at * 1000).toLocaleString()}</span>
                            )}
                            {client.last_seen && (
                              <span><strong>Last Seen:</strong> {new Date(client.last_seen * 1000).toLocaleString()} ({Math.round((Date.now() / 1000) - client.last_seen)}s ago)</span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => moveClient(client.client_id, 'up')}
                      disabled={index === 0}
                      className="p-2"
                    >
                      <ArrowUp className="w-4 h-4" />
                    </Button>

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => moveClient(client.client_id, 'down')}
                      disabled={index === filteredClients.length - 1}
                      className="p-2"
                    >
                      <ArrowDown className="w-4 h-4" />
                    </Button>

                    {/* Unassign button - only show if client has assignments */}
                    {(client.group_id || client.assignment_status !== 'waiting_for_assignment') && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => unassignClient(client.client_id)}
                        className="p-2 text-orange-600 hover:text-orange-700 hover:bg-orange-50"
                        title="Unassign from group/screen"
                      >
                        Unassign
                      </Button>
                    )}

                    {/* Remove button */}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => removeClient(client.client_id)}
                      className="p-2 text-red-600 hover:text-red-700 hover:bg-red-50"
                      title="Remove client completely"
                    >
                      Remove
                    </Button>
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Client Statistics - Updated for active clients only */}
      {clients.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Card className="bg-white border border-gray-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Connected Clients</p>
                  <p className="text-2xl font-bold text-green-600">{clients.length}</p>
                </div>
                <Wifi className="w-8 h-8 text-green-500" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-white border border-gray-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-gray-600">Assigned to Groups</p>
                  <p className="text-2xl font-bold text-blue-600">
                    {clients.filter(c => c.group_id).length}
                  </p>
                </div>
                <Monitor className="w-8 h-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

export default ClientsTab;