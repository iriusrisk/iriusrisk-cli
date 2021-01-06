package io.github.lukacupic.irius.client.commands.countermeasure;

import com.iriusrisk.ApiException;
import com.iriusrisk.api.ProductsApi;
import com.iriusrisk.model.ComponentControl;
import io.github.lukacupic.irius.client.Irius;
import io.github.lukacupic.irius.client.commands.ErrorUtil;
import picocli.CommandLine;

import java.util.List;

@CommandLine.Command(name = "countermeasure", description = "Display countermeasure information")
public class CountermeasureCommand implements Runnable {

    /**
     * Command line Spec for handling missing subcommands.
     */
    @CommandLine.Spec private CommandLine.Model.CommandSpec spec;

    /**
     * The Products API.
     */
    private ProductsApi api;

    /**
     * The API token.
     */
    private String token;

    /**
     * Constructor.
     */
    public CountermeasureCommand() {
        this.api = Irius.getInstance().getApi();
        this.token = Irius.getInstance().getApiToken();
    }

    @CommandLine.Parameters(paramLabel = "<product unique ID>", description = "Product ID")
    private String id;

    @CommandLine.Option(names = {"--required"}, description = "Required countermeasure")
    boolean required;

    @CommandLine.Option(names = {"--implemented"}, description = "Implemented countermeasure")
    boolean implemented;

    @Override
    public void run() {
        try {
            List<ComponentControl> countermeasures;
            if (required) {
                countermeasures = api.productsRefControlsRequiredGet(token, id);

            } else if (implemented) {
                countermeasures = api.productsRefControlsImplementedGet(token, id);

            } else {
                countermeasures = api.productsRefControlsGet(token, id);
            }

            System.out.println(countermeasures);

        } catch (ApiException e) {
            ErrorUtil.apiError(spec);
        }
    }
}