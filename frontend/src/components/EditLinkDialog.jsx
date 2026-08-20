import { useState } from "react";
import { format } from "date-fns";
import { toast } from "sonner";
import { Pencil, CalendarIcon, Loader2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { updateLink } from "@/lib/api";

export const EditLinkDialog = ({ link, onSaved }) => {
  const [open, setOpen] = useState(false);
  const [url, setUrl] = useState(link.url);
  const [expiry, setExpiry] = useState(link.expires_at ? new Date(link.expires_at) : null);
  const [clearExpiry, setClearExpiry] = useState(false);
  const [saving, setSaving] = useState(false);

  const handleOpenChange = (next) => {
    setOpen(next);
    if (next) {
      setUrl(link.url);
      setExpiry(link.expires_at ? new Date(link.expires_at) : null);
      setClearExpiry(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = {};
      if (url.trim() && url.trim() !== link.url) payload.url = url.trim();
      if (clearExpiry) {
        payload.clear_expiry = true;
      } else if (expiry) {
        const end = new Date(expiry);
        end.setHours(23, 59, 59, 999);
        const iso = end.toISOString();
        if (iso !== link.expires_at) payload.expires_at = iso;
      }
      if (Object.keys(payload).length === 0) {
        toast.info("Nothing to update");
        setSaving(false);
        return;
      }
      await updateLink(link.code, payload);
      toast.success(`Updated /${link.code}`);
      setOpen(false);
      onSaved?.();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Could not update link");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogTrigger asChild>
        <Button size="icon" variant="ghost" aria-label={`Edit /${link.code}`} data-testid="links-row-edit-button">
          <Pencil className="h-4 w-4" />
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-md" data-testid="edit-link-dialog">
        <DialogHeader>
          <DialogTitle className="font-heading tracking-tight">
            Edit <span className="font-mono text-primary">/{link.code}</span>
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <p className="text-xs text-muted-foreground">
            The short code stays the same — only the destination and expiry change.
          </p>
          <div className="space-y-2">
            <Label htmlFor={`edit-url-${link.code}`}>Destination URL</Label>
            <Input
              id={`edit-url-${link.code}`}
              data-testid="edit-link-url-input"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="font-mono text-sm"
            />
          </div>
          <div className="space-y-2">
            <Label>Expiration</Label>
            <div className="flex items-center gap-2">
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    type="button"
                    variant="outline"
                    data-testid="edit-link-expiration-trigger"
                    disabled={clearExpiry}
                    className="flex-1 justify-start text-left font-normal"
                  >
                    <CalendarIcon className="mr-2 h-4 w-4 text-muted-foreground" />
                    {clearExpiry ? (
                      <span className="text-muted-foreground">Expiry will be removed</span>
                    ) : expiry ? (
                      format(expiry, "PPP")
                    ) : (
                      <span className="text-muted-foreground">No expiry</span>
                    )}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar
                    mode="single"
                    selected={expiry}
                    onSelect={(d) => {
                      setExpiry(d);
                      setClearExpiry(false);
                    }}
                    disabled={(date) => date < new Date(new Date().setHours(0, 0, 0, 0))}
                    initialFocus
                  />
                </PopoverContent>
              </Popover>
              {(expiry || link.expires_at) && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  data-testid="edit-link-clear-expiry-button"
                  onClick={() => {
                    setClearExpiry(true);
                    setExpiry(null);
                  }}
                >
                  <X className="mr-1 h-3.5 w-3.5" /> Remove
                </Button>
              )}
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)} data-testid="edit-link-cancel-button">
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={saving} data-testid="edit-link-save-button">
            {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Save changes
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
