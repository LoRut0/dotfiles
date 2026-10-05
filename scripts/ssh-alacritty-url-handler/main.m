#import <AppKit/AppKit.h>
#import <CoreServices/CoreServices.h>
#include <stdio.h>
#include <string.h>

static CFStringRef const handlerBundleID = CFSTR("com.lorut0.ssh-alacritty-url-handler");

@interface SSHURLDelegate : NSObject <NSApplicationDelegate>
@end

@implementation SSHURLDelegate

- (void)application:(NSApplication *)application openURLs:(NSArray<NSURL *> *)urls {
    for (NSURL *url in urls) {
        if (![[url.scheme lowercaseString] isEqualToString:@"ssh"] || url.host.length == 0) {
            NSLog(@"Ignoring invalid SSH URL: %@", url);
            continue;
        }

        NSTask *task = [[NSTask alloc] init];
        task.executableURL = [NSURL fileURLWithPath:@"/usr/bin/open"];
        task.arguments = @[
            @"-n", @"-a", @"Alacritty", @"--args", @"-e", @"/usr/bin/ssh", @"--", url.absoluteString
        ];
        NSError *error = nil;
        if (![task launchAndReturnError:&error]) {
            NSLog(@"Could not open SSH URL in Alacritty: %@", error);
        }
    }
    [application terminate:nil];
}

@end

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc == 2 && strcmp(argv[1], "--current") == 0) {
            CFStringRef current = LSCopyDefaultHandlerForURLScheme(CFSTR("ssh"));
            if (current != NULL) {
                NSString *bundleID = CFBridgingRelease(current);
                puts(bundleID.UTF8String);
            } else {
                puts("none");
            }
            return 0;
        }
        if (argc == 2 && strcmp(argv[1], "--register") == 0) {
            OSStatus status = LSSetDefaultHandlerForURLScheme(CFSTR("ssh"), handlerBundleID);
            if (status != noErr) {
                fprintf(stderr, "Could not set SSH URL handler: %d\n", (int)status);
                return 1;
            }
            CFStringRef current = LSCopyDefaultHandlerForURLScheme(CFSTR("ssh"));
            BOOL registered = current != NULL && CFStringCompare(current, handlerBundleID, 0) == kCFCompareEqualTo;
            if (current != NULL) CFRelease(current);
            if (!registered) {
                fputs("SSH URL handler did not become the default\n", stderr);
                return 1;
            }
            puts("Registered as the default SSH URL handler");
            return 0;
        }

        NSApplication *application = [NSApplication sharedApplication];
        SSHURLDelegate *delegate = [[SSHURLDelegate alloc] init];
        application.delegate = delegate;
        [application run];
    }
    return 0;
}
