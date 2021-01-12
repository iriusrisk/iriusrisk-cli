package com.iriusrisk.cli.commands.configure;

import com.iriusrisk.cli.commands.ErrorUtil;

import java.io.IOException;

import picocli.CommandLine;

@CommandLine.Command(name = "url", description = "Manage url configuration properties")
public class UrlCommand implements Runnable {

    /**
     * Command line Spec for handling missing subcommands.
     */
    @CommandLine.Spec private CommandLine.Model.CommandSpec spec;

    /**
     * Constructor.
     */
    public UrlCommand() {
    }

    @CommandLine.Command(name = "set", description = "Sets the url to be used by iriusrusk-cli")
    void setCommand(@CommandLine.Parameters(paramLabel = "<url>", description = "url") String url) {
        if (url.isEmpty()) {
            ErrorUtil.customError(spec, "URL cannot be empty");
        }

        try {
            CredentialUtils.writeUrlCredentials(url);
        } catch (IOException e) {
            ErrorUtil.customError(spec, "Error while writing to credentials file");
        }
    }

    @Override
    public void run() {
        ErrorUtil.subcommandError(spec);
    }
}
