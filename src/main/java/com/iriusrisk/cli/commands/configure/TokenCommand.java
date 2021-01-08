package com.iriusrisk.cli.commands.configure;

import com.iriusrisk.cli.Irius;
import com.iriusrisk.cli.commands.ErrorUtil;
import picocli.CommandLine;

import java.io.IOException;

@CommandLine.Command(name = "token", description = "Manage token-related configuration properties")
public class TokenCommand implements Runnable {

    /**
     * Command line Spec for handling missing subcommands.
     */
    @CommandLine.Spec private CommandLine.Model.CommandSpec spec;

    /**
     * Constructor.
     */
    public TokenCommand() {
    }

    @CommandLine.Command(name = "set", description = "Sets the value of the token")
    void setCommand(@CommandLine.Parameters(paramLabel = "<api token>", description = "API token") String token) {
        if (token.isEmpty()) {
            ErrorUtil.customError(spec, "API token cannot be empty");
        }

        try {
            Irius.setApiToken(token);
            CredentialUtils.writeTokenCredential(token);
        } catch (IOException e) {
            ErrorUtil.customError(spec, "Error while writing to credentials file");
        }
    }

    @Override
    public void run() {
        ErrorUtil.subcommandError(spec);
    }
}