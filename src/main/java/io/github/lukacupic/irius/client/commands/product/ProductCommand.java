package io.github.lukacupic.irius.client.commands.product;

import com.iriusrisk.ApiException;
import com.iriusrisk.api.ProductsApi;
import com.iriusrisk.model.Product;
import com.iriusrisk.model.ProductShort;
import io.github.lukacupic.irius.client.Irius;
import io.github.lukacupic.irius.client.commands.ErrorUtil;
import picocli.CommandLine;

import java.util.List;

@CommandLine.Command(name = "product", description = "Display product-related information")
public class ProductCommand implements Runnable {

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
    public ProductCommand() {
        this.api = Irius.getInstance().getApi();
        this.token = Irius.getInstance().getApiToken();

    }

    @CommandLine.Command(name = "list", description = "List all products")
    void listCommand() {
        try {
            List<ProductShort> products = api.productsGet(token, null, null, null);
            products.forEach(System.out::println);

        } catch (ApiException e) {
            ErrorUtil.apiError(spec);
        }
    }

    @CommandLine.Command(name = "show", description = "Display product details")
    void showCommand(@CommandLine.Parameters(paramLabel = "<product unique ID>", description = "Product ID") String id) {
        try {
            Product product = api.productsRefGet(token, id);
            System.out.println(product);

        } catch (ApiException e) {
            ErrorUtil.apiError(spec);
        }
    }

    @Override
    public void run() {
        ErrorUtil.subcommandError(spec);
    }
}